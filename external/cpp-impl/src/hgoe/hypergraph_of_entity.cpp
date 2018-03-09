//
// Created by jldevezas on 3/6/18.
//

#define BOOST_LOG_DYN_LINK 1

#include <chrono>
#include <utility>

#include <boost/log/trivial.hpp>
#include <boost/python/extract.hpp>
#include <boost/tokenizer.hpp>
#include <boost/algorithm/string.hpp>
#include <boost/python/list.hpp>
#include <boost/python/tuple.hpp>
#include <boost/filesystem.hpp>

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

namespace py = boost::python;

HypergraphOfEntity::HypergraphOfEntity() {

}

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
    std::vector<triple> triples = std::vector<triple>();
    if (!pyTriples.is_none()) {
        py::list pyTriplesList = py::extract<py::list>(document.attr("triples"));
        while (py::len(pyTriplesList) > 0) {
            py::tuple pyTriple = py::extract<py::tuple>(pyTriplesList.pop());

            py::object pySubj = py::extract<py::object>(pyTriple[0]);
            std::string subj = py::extract<std::string>(pySubj.attr("label"));

            std::string pred = py::extract<std::string>(pyTriple[1]);

            py::object pyObj = py::extract<py::object>(pyTriple[2]);
            std::string obj = py::extract<std::string>(pyObj.attr("label"));

            triples.push_back(triple {subj, pred, obj});
        }
    }

    Document doc = Document(docID, entity, text, triples);
    //std::cout << doc << std::endl;
    index(doc);
}

void HypergraphOfEntity::index(Document document) {
    auto startTime = std::chrono::system_clock::now().time_since_epoch();

    indexDocument(std::move(document));

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
    Node *sourceDocumentNode = this->hg.getOrCreateNode(new DocumentNode(document.getDocID()));

    std::set<Node *> targetNodes = indexEntities(document);

    std::vector<std::string> tokens = analyze(document.getText());
    if (tokens.empty()) return;

    for (auto token : tokens) {
        targetNodes.insert(this->hg.getOrCreateNode(new TermNode(token)));
    }

    // TODO Consider changing directed to undirected hyperedge.
    Edge *edge = new DocumentEdge(document.getDocID(), {sourceDocumentNode}, targetNodes);
    this->hg.createEdge(edge);
}

std::set<Node *> HypergraphOfEntity::indexEntities(Document document) {
    std::set<Node *> nodes = std::set<Node *>();

    for (auto triple : document.getTriples()) {
        nodes.insert(this->hg.getOrCreateNode(new EntityNode(&document, triple.subject)));
        nodes.insert(this->hg.getOrCreateNode(new EntityNode(&document, triple.object)));
    }

    this->hg.createEdge(new RelatedToEdge(nodes));

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
        if (entityNode->label() == NodeLabel::ENTITY) {
            std::vector<std::string> tokens = analyze(entityNode->getName());
            std::set<Node *> termNodes = std::set<Node *>();
            for (auto token : tokens) {
                if (trie.find(token) != trie.end()) {
                    auto optTermNode = this->hg.getNodes().find(new TermNode(token));
                    if (optTermNode != this->hg.getNodes().end()) {
                        termNodes.insert(*optTermNode);
                    }
                }
            }

            if (termNodes.empty()) continue;

            this->hg.createEdge(new ContainedInEdge(termNodes, {entityNode}));
        }
    }
}

void HypergraphOfEntity::postProcessing() {
    linkTextAndKnowledge();
}

void HypergraphOfEntity::save() {
    boost::filesystem::create_directories(baseDirPath);
    this->hg.save(baseDirPath.string());
}

void HypergraphOfEntity::load() {
    this->hg = Hypergraph::load(baseDirPath.string());
}
