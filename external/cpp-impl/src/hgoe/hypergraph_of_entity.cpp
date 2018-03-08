//
// Created by jldevezas on 3/6/18.
//

#define BOOST_LOG_DYN_LINK 1

#include <chrono>
#include <hgoe/hypergraph_of_entity.h>
#include <hgoe/nodes/node.h>
#include <hgoe/hypergraph.h>
#include <boost/log/trivial.hpp>
#include <boost/python/extract.hpp>
#include <boost/tokenizer.hpp>
#include <boost/algorithm/string.hpp>
#include <boost/python/list.hpp>
#include <boost/python/tuple.hpp>
#include <hgoe/edges/document_edge.h>
#include <hgoe/nodes/term_node.h>
#include <hgoe/nodes/document_node.h>
#include <structures/document.h>
#include <hgoe/nodes/entity_node.h>
#include <hgoe/edges/related_to_edge.h>

namespace py = boost::python;

HypergraphOfEntity::HypergraphOfEntity() {
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
    std::vector<triple> triples = std::vector<triple>();
    if (!pyTriples.is_none()) {
        py::list pyTriplesList = py::extract<py::list>(document.attr("triples"));
        while (py::len(pyTriplesList) > 0) {
            py::tuple pyTriple = py::extract<py::tuple>(pyTriplesList.pop());
            std::string subj = py::extract<std::string>(pyTriple[0]);
            std::string pred = py::extract<std::string>(pyTriple[1]);
            std::string obj = py::extract<std::string>(pyTriple[2]);
            triples.push_back(triple {subj, pred, obj});
        }
    }

    Document doc = Document(docID, entity, text, triples);
    std::cout << doc << std::endl;
    index(doc);
}

void HypergraphOfEntity::index(Document document) {
    auto startTime = std::chrono::high_resolution_clock::now();

    indexDocument(document);

    auto time = std::chrono::high_resolution_clock::now() - startTime;
    this->totalTime += time;

    this->counter++;
    avgTimePerDocument = counter > 1 ? (avgTimePerDocument * (counter - 1) + time) / counter : time;

    if (counter % 100 == 0) {
        BOOST_LOG_TRIVIAL(info)
            << counter << "indexed documents in" << totalTime.count()
            << '(' << avgTimePerDocument.count()
            << "/doc, " << counter * 3600000 / totalTime.count() << " docs/h)";
    }
}


void HypergraphOfEntity::indexDocument(Document document) {
    Node sourceDocumentNode = this->hg.getOrCreateNode(DocumentNode(document.getDocID()));

    std::set<Node> targetNodes = indexEntities(document);

    std::vector<std::string> tokens = analyze(document.getText());
    if (tokens.empty()) return;

    for (auto token : tokens) {
        targetNodes.insert(this->hg.getOrCreateNode(TermNode(token)));
    }

    // TODO Consider changing directed to undirected hyperedge.
    this->hg.createEdge(DocumentEdge(document.getDocID(), {sourceDocumentNode}, targetNodes));
}

std::set<Node> HypergraphOfEntity::indexEntities(Document document) {
    std::set<Node> nodes = std::set<Node>();

    for (auto triple : document.getTriples()) {
        nodes.insert(this->hg.getOrCreateNode(EntityNode(&document, triple.subject)));
        nodes.insert(this->hg.getOrCreateNode(EntityNode(&document, triple.object)));
    }

    this->hg.createEdge(RelatedToEdge(nodes));

    return nodes;
}

void HypergraphOfEntity::linkTextAndKnowledge() {
    /*logger.info("Building trie from term nodes");
    Trie.TrieBuilder
    trieBuilder = Trie.builder()
            .ignoreOverlaps()
            .ignoreCase()
            .onlyWholeWords();

    for (int termNodeID : graph.getVertices()) {
        Node termNode = nodeIndex.getKey(termNodeID);
        if (termNode instanceof TermNode) {
            trieBuilder.addKeyword(termNode.getName());
        }
    }

    Trie trie = trieBuilder.build();

    logger.info("Creating links between entity nodes and term nodes using trie");
    for (int entityNodeID : graph.getVertices()) {
        Node entityNode = nodeIndex.getKey(entityNodeID);
        if (entityNode instanceof EntityNode) {
            Collection <Emit> emits = trie.parseText(entityNode.getName());
            Set <Integer> termNodes = emits.stream()
                    .map(e->nodeIndex.get(new TermNode(e.getKeyword())))
                    .collect(Collectors.toSet());

            if (termNodes.isEmpty()) continue;

            ContainedInEdge containedInEdge = new ContainedInEdge();
            int edgeID = createDirectedEdge(containedInEdge);
            addNodesToHyperEdgeTail(edgeID, termNodes);
            graph.addToDirectedHyperEdgeHead(edgeID, entityNodeID);
        }
    }*/
}