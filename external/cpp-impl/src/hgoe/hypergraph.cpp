//
// Created by jldevezas on 3/6/18.
//

#include <fstream>

#include <omp.h>
#include <boost/log/trivial.hpp>

#include <hgoe/hypergraph.h>

BOOST_CLASS_EXPORT_IMPLEMENT(Hypergraph)

boost::shared_ptr<Node> Hypergraph::getOrCreateNode(boost::shared_ptr<Node> node) {
    if (Hypergraph::nodes.insert(node).second) {
        return node;
    }

    return *nodes.find(node);
}

const NodeSet &Hypergraph::getNodes() const {
    return nodes;
}

boost::shared_ptr<Edge> Hypergraph::createEdge(boost::shared_ptr<Edge> edge) {
    Hypergraph::edges.insert(edge);
    if (edge->isDirected()) {
        BOOST_LOG_TRIVIAL(trace) << "Directed edge with "
                                 << edge->getTail().size() << " tail nodes and "
                                 << edge->getHead().size() << " head nodes";


        #pragma omp parallel
        {
            for (auto nodeIt = edge->getTail().begin(); nodeIt != edge->getTail().end(); nodeIt++) {
                #pragma omp critical
                {
                    if (outEdges.find(*nodeIt) == outEdges.end())
                        outEdges[*nodeIt] = boost::make_shared<EdgeSet>();
                    outEdges[*nodeIt]->insert(edge);
                }
            }
        }

        #pragma omp parallel
        {
            for (auto nodeIt = edge->getTail().begin(); nodeIt != edge->getHead().end(); nodeIt++) {
                #pragma omp critical
                {
                    if (inEdges.find(*nodeIt) == inEdges.end())
                        inEdges[*nodeIt] = boost::make_shared<EdgeSet>();
                    inEdges[*nodeIt]->insert(edge);
                }
            }
        }
    } else {
        BOOST_LOG_TRIVIAL(trace) << "Undirected edge with " << edge->getNodes().size() << " nodes";

        #pragma omp parallel
        {
            for (auto nodeIt = edge->getTail().begin(); nodeIt != edge->getNodes().end(); nodeIt++) {
                #pragma omp critical
                {
                    if (outEdges.find(*nodeIt) == outEdges.end())
                        outEdges[*nodeIt] = boost::make_shared<EdgeSet>();
                    outEdges[*nodeIt]->insert(edge);

                    if (inEdges.find(*nodeIt) == inEdges.end())
                        inEdges[*nodeIt] = boost::make_shared<EdgeSet>();
                    inEdges[*nodeIt]->insert(edge);
                }
            }
        }
    }
    return edge;
}

const EdgeSet &Hypergraph::getEdges() const {
    return edges;
}

EdgeSet Hypergraph::getOutEdges(boost::shared_ptr<Node> node) {
    auto edgeSetIt = this->outEdges.find(node);
    if (edgeSetIt == this->outEdges.end()) {
        return EdgeSet();
    }
    return *(edgeSetIt->second);
}

EdgeSet Hypergraph::getInEdges(boost::shared_ptr<Node> node) {
    auto edgeSetIt = this->inEdges.find(node);
    if (edgeSetIt == this->inEdges.end()) {
        return EdgeSet();
    }
    return *(edgeSetIt->second);
}

// FIXME inefficient
const EdgeSet Hypergraph::getAllEdges(boost::shared_ptr<Node> node) const {
    EdgeSet allEdges;
    allEdges.insert(outEdges.at(node)->begin(), outEdges.at(node)->end());
    allEdges.insert(inEdges.at(node)->begin(), inEdges.at(node)->end());
    return allEdges;
}

void Hypergraph::save(std::string path) {
    std::ofstream ofs(path);
    boost::archive::binary_oarchive oa(ofs);
    oa << this;
    ofs.close();
}

Hypergraph Hypergraph::load(std::string path) {
    Hypergraph *hg;
    std::ifstream ifs(path);
    boost::archive::binary_iarchive ia(ifs);
    ia >> hg;
    ifs.close();
    return *hg;
}

unsigned long Hypergraph::nodeCount() {
    return nodes.size();
}

unsigned long Hypergraph::edgeCount() {
    return edges.size();
}
