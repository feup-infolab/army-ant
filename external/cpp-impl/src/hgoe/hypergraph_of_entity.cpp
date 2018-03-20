//
// Created by jldevezas on 3/6/18.
//

#include <chrono>
#include <utility>

#include <boost/log/trivial.hpp>
#include <boost/python/extract.hpp>
#include <boost/tokenizer.hpp>
#include <boost/algorithm/string.hpp>
#include <boost/python/list.hpp>
#include <boost/python/tuple.hpp>
#include <boost/filesystem.hpp>
#include <boost/shared_ptr.hpp>
#include <boost/unordered_set.hpp>
#include <boost/container/map.hpp>
#include <boost/random/uniform_int_distribution.hpp>
#include <boost/random/mersenne_twister.hpp>
#include <boost/range/algorithm/max_element.hpp>
#include <boost/container/detail/pair.hpp>
#include <boost/range/algorithm/set_algorithm.hpp>

#include <tsl/htrie_map.h>
#include <tsl/htrie_set.h>

#include <structures/document.h>
#include <structures/entity.h>
#include <hgoe/hypergraph_of_entity.h>
#include <hgoe/nodes/node.h>
#include <hgoe/hypergraph.h>
#include <hgoe/edges/document_edge.h>
#include <hgoe/nodes/term_node.h>
#include <hgoe/nodes/document_node.h>
#include <hgoe/nodes/entity_node.h>
#include <hgoe/edges/related_to_edge.h>
#include <hgoe/edges/contained_in_edge.h>
#include <boost/numeric/conversion/cast.hpp>

namespace py = boost::python;

const unsigned int HypergraphOfEntity::DEFAULT_WALK_LENGTH = 2;
const unsigned int HypergraphOfEntity::DEFAULT_WALK_REPEATS = 100;
const float HypergraphOfEntity::PROBABILITY_THRESHOLD = 0.005;

HypergraphOfEntity::HypergraphOfEntity() = default;

HypergraphOfEntity::HypergraphOfEntity(std::string path) {
    this->baseDirPath = boost::filesystem::path(path);
    this->hgFilePath = this->baseDirPath / boost::filesystem::path("hypergraph.idx");
    this->hg = Hypergraph();
    this->totalTime = std::chrono::duration<long>();
    this->counter = 0;
}

void HypergraphOfEntity::pyIndex(py::object document) {
    std::string docID = py::extract<std::string>(document.attr("doc_id"));

    py::object pyText = py::extract<py::object>(document.attr("text"));
    std::string text;
    if (!pyText.is_none()) {
        text = py::extract<std::string>(pyText);
    }

    py::object pyEntity = py::extract<py::object>(document.attr("entity"));
    std::string entity;
    if (!pyEntity.is_none()) {
        entity = py::extract<std::string>(pyEntity);
    }

    py::object pyTriples = py::extract<py::object>(document.attr("triples"));
    std::vector<Triple> triples = std::vector<Triple>();
    if (!pyTriples.is_none()) {
        py::list pyTriplesList = py::extract<py::list>(document.attr("triples"));
        while (py::len(pyTriplesList) > 0) {
            py::tuple pyTriple = py::extract<py::tuple>(pyTriplesList.pop());

            py::object pySubj = py::extract<py::object>(pyTriple[0]);
            std::string subj = py::extract<std::string>(pySubj.attr("label"));

            std::string pred = py::extract<std::string>(pyTriple[1]);

            py::object pyObj = py::extract<py::object>(pyTriple[2]);
            std::string obj = py::extract<std::string>(pyObj.attr("label"));

            triples.push_back(Triple {subj, pred, obj});
        }
    }

    Document doc = Document(docID, entity, text, triples);
    //std::cout << doc << std::endl;
    index(doc);
}

void HypergraphOfEntity::index(Document document) {
    auto startTime = std::chrono::system_clock::now().time_since_epoch();

    indexDocument(boost::move(document));

    auto endTime = std::chrono::system_clock::now().time_since_epoch();
    auto time = std::chrono::duration_cast<std::chrono::milliseconds>(endTime - startTime);
    this->totalTime += time;

    this->counter++;
    avgTimePerDocument =
            counter > 1 ? (avgTimePerDocument * (counter - 1) + time.count()) / (float) counter : (float) time.count();

    if (counter % 100 == 0) {
        BOOST_LOG_TRIVIAL(info)
            << counter << " indexed documents in " << totalTime.count() << "ms "
            << '(' << avgTimePerDocument << " ms/doc, "
            << counter * 3600000 / totalTime.count() << " docs/h)";
    }
}


void HypergraphOfEntity::indexDocument(Document document) {
    BOOST_LOG_TRIVIAL(trace) << "Creating document node";
    boost::shared_ptr<Node> sourceDocumentNode = this->hg.getOrCreateNode(
            boost::make_shared<DocumentNode>(document.getDocID()));

    BOOST_LOG_TRIVIAL(trace) << "Indexing entities";
    NodeSet targetNodes = indexEntities(document);

    BOOST_LOG_TRIVIAL(trace) << "Tokenizing document";
    std::vector<std::string> tokens = analyze(document.getText());
    if (tokens.empty()) return;

    for (auto token : tokens) {
        BOOST_LOG_TRIVIAL(trace) << "Creating term node for '" << token << "'";
        targetNodes.insert(this->hg.getOrCreateNode(boost::make_shared<TermNode>(token)));
    }

    // TODO Consider changing directed to undirected hyperedge.
    BOOST_LOG_TRIVIAL(trace) << "Creating document edge";
    auto edge = boost::make_shared<DocumentEdge>(document.getDocID(), NodeSet({sourceDocumentNode}), targetNodes);
    this->hg.createEdge(edge);
}

NodeSet HypergraphOfEntity::indexEntities(Document document) {
    NodeSet nodes = NodeSet();

    for (auto triple : document.getTriples()) {
        nodes.insert(this->hg.getOrCreateNode(boost::make_shared<EntityNode>(&document, triple.subject)));
        nodes.insert(this->hg.getOrCreateNode(boost::make_shared<EntityNode>(&document, triple.object)));
    }

    this->hg.createEdge(boost::make_shared<RelatedToEdge>(nodes));

    return nodes;
}

void HypergraphOfEntity::linkTextAndKnowledge() {
    tsl::htrie_set<char> trie = tsl::htrie_set<char>();

    BOOST_LOG_TRIVIAL(info) << "Building trie from term nodes";

    for (auto node : this->hg.getNodes()) {
        trie.insert(node->getName());
    }

    BOOST_LOG_TRIVIAL(info) << "Creating links between entity nodes and term nodes using trie";
    for (auto entityNode : this->hg.getNodes()) {
        if (entityNode->label() == Node::Label::ENTITY) {
            std::vector<std::string> tokens = analyze(entityNode->getName());
            NodeSet termNodes = NodeSet();
            for (auto token : tokens) {
                if (trie.find(token) != trie.end()) {
                    auto optTermNode = this->hg.getNodes().find(boost::make_shared<TermNode>(token));
                    if (optTermNode != this->hg.getNodes().end()) {
                        termNodes.insert(*optTermNode);
                    }
                }
            }

            if (termNodes.empty()) continue;

            this->hg.createEdge(boost::make_shared<ContainedInEdge>(termNodes, NodeSet({entityNode})));
        }
    }
}

void HypergraphOfEntity::postProcessing() {
    linkTextAndKnowledge();
}

void HypergraphOfEntity::save() {
    boost::filesystem::create_directories(baseDirPath);
    this->hg.save(hgFilePath.string());
}

void HypergraphOfEntity::load() {
    this->hg = Hypergraph::load(hgFilePath.string());
}

NodeSet HypergraphOfEntity::getQueryTermNodes(const std::vector<std::string> &terms) {
    NodeSet termNodes;

    for (const auto &term : terms) {
        auto termNodeIt = hg.getNodes().find(boost::make_shared<TermNode>(term));
        if (termNodeIt != hg.getNodes().end()) {
            termNodes.insert(*termNodeIt);
        }
    }

    return termNodes;
}

NodeSet HypergraphOfEntity::getSeedNodes(const NodeSet &queryTermNodes) {
    NodeSet seedNodes;

    for (const auto &queryTermNode : queryTermNodes) {
        NodeSet localSeedNodes;

        EdgeSet edgeSet;
        auto queryTermNodeIt = hg.getNodes().find(queryTermNode);
        if (queryTermNodeIt != hg.getNodes().end()) {
            edgeSet = hg.getOutEdges(queryTermNode);
        }

        //if (edgesIt == hg.getOutEdges().end()) continue;

        for (const auto &edge : edgeSet) {
            if (edge->label() != Edge::Label::CONTAINED_IN) continue;

            for (const auto &node : edge->getHead()) {
                if (node->label() == Node::Label::ENTITY) {
                    localSeedNodes.insert(node);
                }
            }
        }

        if (localSeedNodes.empty() && queryTermNodeIt != hg.getNodes().end()) {
            localSeedNodes.insert(queryTermNode);
        }

        seedNodes.insert(localSeedNodes.begin(), localSeedNodes.end());
    }

    return seedNodes;
}

NodeSet HypergraphOfEntity::getUndirectedNeighborsPerEdgeType(boost::shared_ptr<Node> sourceNode,
                                                              Edge::Label edgeLabel) {
    NodeSet result;

    for (const auto &edge : hg.getAllEdges(sourceNode)) {
        if (edge->label() != edgeLabel) continue;
        if (edge->isDirected()) {
            result.insert(edge->getTail().begin(), edge->getTail().end());
            result.insert(edge->getHead().begin(), edge->getHead().end());
        } else {
            result.insert(edge->getNodes().begin(), edge->getNodes().end());
        }
        result.erase(sourceNode);
    }

    return result;
}

double HypergraphOfEntity::confidenceWeight(boost::shared_ptr<Node> seedNode, const NodeSet &queryTermNodes) {
    // Shouldn't need this.
    //auto seedNodeIt = hg.getNodes().find(seedNode);
    //if (seedNodeIt == hg.getNodes().end()) return 0;

    if (seedNode->label() == Node::Label::TERM) return 1;

    NodeSet neighbors = getUndirectedNeighborsPerEdgeType(seedNode, Edge::Label::CONTAINED_IN);

    NodeSet linkedQueryTermNodes;
    linkedQueryTermNodes.insert(neighbors.begin(), neighbors.end());
    // FIXME set_intersect?
    for (const auto &linkedQueryTermNode : linkedQueryTermNodes) {
        auto nodeIt = queryTermNodes.find(linkedQueryTermNode);
        if (nodeIt == queryTermNodes.end()) {
            linkedQueryTermNodes.erase(nodeIt);
        }
    }

    if (neighbors.empty()) return 0;

    return (double) linkedQueryTermNodes.size() / neighbors.size();
}

WeightedNodeSet HypergraphOfEntity::seedNodeConfidenceWeights(const NodeSet &seedNodes, const NodeSet &queryTermNodes) {
    WeightedNodeSet weightedSeedNodes;

    for (const auto &seedNode : seedNodes) {
        weightedSeedNodes[seedNode] = confidenceWeight(seedNode, queryTermNodes);
    }

    return weightedSeedNodes;
}

// TODO Should follow Bellaachia2013 for random walks on hypergraphs (Equation 14)
template<typename T>
typename T::value_type HypergraphOfEntity::getRandom(T &elementSet) {
    boost::random::mt19937 rng;
    boost::random::uniform_int_distribution<> randomBucket(0, boost::numeric_cast<int>(elementSet.bucket_count()) - 1);
    unsigned long bucket;
    do {
        bucket = boost::numeric_cast<unsigned long>(randomBucket(rng));
    } while (elementSet.bucket_size(bucket) < 1);

    boost::random::uniform_int_distribution<> randomIndex(0,
                                                          boost::numeric_cast<int>(elementSet.bucket_size(bucket) - 1));
    auto elementIt = elementSet.begin();
    boost::advance(elementIt, randomIndex(rng));
    return *elementIt;
}

Path HypergraphOfEntity::randomWalk(boost::shared_ptr<Node> startNode, unsigned int length) {
    Path path;
    path.push_back(startNode);
    HypergraphOfEntity::randomStep(startNode, length, path);
    return path;
}

void HypergraphOfEntity::randomStep(boost::shared_ptr<Node> node, unsigned int remainingSteps, Path &path) {
    if (remainingSteps == 0) return;

    EdgeSet edges = hg.getOutEdges(node);

    if (edges.empty()) return;
    boost::shared_ptr<Edge> randomEdge = HypergraphOfEntity::getRandom(edges);

    NodeSet nodes;
    if (randomEdge->isDirected()) {
        nodes.insert(randomEdge->getHead().begin(), randomEdge->getHead().end());
    } else {
        nodes.insert(randomEdge->getNodes().begin(), randomEdge->getNodes().end());
        nodes.erase(node);
    }

    if (nodes.empty()) return;
    boost::shared_ptr<Node> randomNode = HypergraphOfEntity::getRandom(nodes);

    path.push_back(randomNode);
    randomStep(randomNode, remainingSteps - 1, path);
}

ResultSet HypergraphOfEntity::randomWalkSearch(const NodeSet &seedNodes, WeightedNodeSet &seedNodeWeights,
                                               unsigned int walkLength, unsigned int walkRepeats) {
    BOOST_LOG_TRIVIAL(info) << "WALK_LENGTH = " << walkLength << ", WALK_REPEATS = " << walkRepeats;

    WeightedNodeSet weightedNodeVisitProbability;
    WeightedNodeSet nodeCoverage;

/*
    trace.add("Random walk search (WALK_LENGTH = %d, WALK_REPEATS = %d)", walk_length, walk_repeats);
    trace.goDown();
*/

    for (auto const &seedNode : seedNodes) {
        IntWeightedNodeSet nodeVisits;
//        trace.add("From seed node: %s", nodeIndex.getKey(seedNode));
        /*trace.goDown();
        trace.add("Random walk with restart (WALK_LENGTH = %d, WALK_REPEATS = %d)", WALK_LENGTH, WALK_REPEATS);
        trace.goDown();*/

        for (int i = 0; i < walkRepeats; i++) {
            auto randomPath = randomWalk(seedNode, walkLength);

            /*String messageRandomPath = Arrays.stream(randomPath.toVertexArray())
                    .mapToObj(nodeID -> nodeIndex.getKey(nodeID).toString())
                    .collect(Collectors.joining        //IntSet edgeIDs = graph.getEdgesIncidentTo(nodeID);
(" -> "));
            trace.add(messageRandomPath.replace("%", "%%"));
            trace.goDown();*/

            for (auto node : randomPath) {
                nodeVisits[node]++;
                //trace.add("Node %s visited %d times", nodeIndex.getKey(nodeID), nodeVisits.get(nodeID));
            }

            //trace.goUp();
        }

        //trace.goUp();

        auto maxVisitsIt = std::max_element(
                nodeVisits.begin(), nodeVisits.end(),
                [](const std::pair<boost::shared_ptr<Node>, int> &a,
                   const std::pair<boost::shared_ptr<Node>, int> &b) {
                    return a.second < b.second;
                });
        int maxVisits = 0;
        if (maxVisitsIt != nodeVisits.end())
            maxVisits = maxVisitsIt->second;

/*
        trace.goDown();
        trace.add("max(visits) = %d", maxVisits);
*/

        /*trace.add("Accumulating visit probability, weighted by seed node confidence");
        trace.goDown();*/
        for (auto entry : nodeVisits) {
            nodeCoverage[entry.first]++;
            weightedNodeVisitProbability[entry.first] +=
                    nodeVisits[entry.first] / maxVisits * seedNodeWeights[seedNode];
            /*trace.add("score(%s) += visits(%s) * w(%s)",
                    nodeIndex.getKey(nodeID),
                    nodeIndex.getKey(nodeID),
                    nodeIndex.getKey(seedNodeID));
            trace.goDown();
            trace.add("P(visit(%s)) = %f", nodeIndex.getKey(nodeID).toString(), (float) nodeVisits.get(nodeID) / maxVisits);
            trace.add("w(%s) = %f", nodeIndex.getKey(seedNodeID), seedNodeWeights.get(seedNodeID));
            trace.add("score(%s) = %f", nodeIndex.getKey(nodeID), weightedNodeVisitProbability.get(nodeID));
            trace.goUp();*/
        }

/*
        trace.add("%d visited nodes", nodeVisits.size());
        trace.goUp();
*/

        /*trace.goUp();
        trace.goUp();*/
    }

    //trace.goUp();

    ResultSet resultSet = ResultSet();
    //resultSet.setTrace(trace);

/*
    trace.add("Weighted nodes");
    trace.goDown();
*/

    auto maxCoverageIt = std::max_element(
            nodeCoverage.begin(), nodeCoverage.end(),
            [](const std::pair<boost::shared_ptr<Node>, int> &a,
               const std::pair<boost::shared_ptr<Node>, int> &b) {
                return a.second < b.second;
            });
    double maxCoverage = 0;
    if (maxCoverageIt != nodeCoverage.end())
        maxCoverage = maxCoverageIt->second;
//    trace.add("max(coverage) = %f", maxCoverage);

    for (auto entry : weightedNodeVisitProbability) {
        nodeCoverage[entry.first] /= maxCoverage;

/*
        trace.add(node.toString().replace("%", "%%"));
        trace.goDown();
        trace.add("score = %f", weightedNodeVisitProbability.get(nodeID));
        trace.add("coverage = %f", nodeCoverage.get(nodeID));
        trace.goUp();
*/

        if (entry.first->label() == Node::Label::ENTITY) {
            auto entityNode = boost::static_pointer_cast<EntityNode>(entry.first);
            BOOST_LOG_TRIVIAL(debug) << "Ranking " << *entityNode << " using RANDOM_WALK_SCORE";
            double score = nodeCoverage[entry.first] * weightedNodeVisitProbability[entry.first];
            // XXX TODO FIXME issue here
            if (score > PROBABILITY_THRESHOLD && entityNode->hasDocID()) {
                /*resultSet.addReplaceResult(
                        Result(score, entry.first, entityNode->getDocID()));*/
                resultSet.addReplaceResult(
                        Result(score, entityNode->getDocID()));
            }
            /*if (score > PROBABILITY_THRESHOLD) {
                if (entityNode.hasDocID()) {
                    resultSet.addReplaceResult(new Result(score, entityNode, entityNode.getDocID()));
                } else {
                    resultSet.addReplaceResult(new Result(score, entityNode, entityNode.getName()));
                }
            }*/
        }
    }

    /*trace.goUp();

    trace.add("Collecting results (class=EntityNode; hasDocID()=true)");
    trace.goDown();

    for (Result result : resultSet) {
        trace.add(result.getNode().toString());
        trace.goDown();
        trace.add("score = %f", result.getScore());
        trace.add("docID = %s", result.getDocID());
        trace.add("nodeID = %d", nodeIndex.get(result.getNode()));
        trace.goUp();
    }*/

    return resultSet;
}

ResultSet HypergraphOfEntity::search(std::string query, unsigned int offset, unsigned int limit) {
    return search(query, offset, limit, RankingFunction::RANDOM_WALK,
                  RankingParams({{"l", DEFAULT_WALK_LENGTH},
                                 {"r", DEFAULT_WALK_REPEATS}}));
}

ResultSet HypergraphOfEntity::search(std::string query, unsigned int offset, unsigned int limit,
                                     RankingFunction function, RankingParams params) {
    std::vector<std::string> tokens = analyze(query);
    NodeSet queryTermNodes = getQueryTermNodes(tokens);
/*
    trace.add("Mapping query terms [ %s ] to query term nodes", StringUtils.join(tokens, ", "));
    trace.goDown();
    for (int queryTermNodeID : queryTermNodes) {
        trace.add(nodeIndex.getKey(queryTermNodeID).toString());
    }
    trace.goUp();
*/

    NodeSet seedNodes = getSeedNodes(queryTermNodes);
    std::cout << "Seed Nodes: " << seedNodes << std::endl;
/*
    trace.add("Mapping query term nodes to seed nodes");
    trace.goDown();
    for (int seedNodeID : seedNodes) {
        trace.add(nodeIndex.getKey(seedNodeID).toString().replace("%", "%%"));
    }
    trace.goUp();
*/

    WeightedNodeSet seedNodeWeights = seedNodeConfidenceWeights(seedNodes, queryTermNodes);
    //System.out.println("Seed Node Confidence Weights: " + seedNodeWeights);
    BOOST_LOG_TRIVIAL(info) << seedNodeWeights.size() << " seed nodes weights calculated for [ " << query << " ]";
/*
    trace.add("Calculating confidence weight for seed nodes");
    trace.goDown();
    for (Map.Entry < Integer, Double > entry : seedNodeWeights.entrySet()) {
        trace.add("w(%s) = %f", nodeIndex.getKey(entry.getKey()), entry.getValue());
    }
    trace.goUp();
*/

    ResultSet resultSet = randomWalkSearch(seedNodes, seedNodeWeights, DEFAULT_WALK_LENGTH, DEFAULT_WALK_REPEATS);

    BOOST_LOG_TRIVIAL(info) << resultSet.getNumDocs() << " entities ranked for [ " << query << " ]";
    return resultSet;
}

ResultSet HypergraphOfEntity::pySearch(py::object query, py::object offset, py::object limit) {
    return search(
            py::extract<std::string>(query),
            py::extract<unsigned int>(offset),
            py::extract<unsigned int>(limit));
}