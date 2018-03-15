//
// Created by jldevezas on 3/5/18.
//

#include <iostream>

#include <boost/filesystem.hpp>

#include <hgoe/hypergraph.h>
#include <hgoe/nodes/term_node.h>
#include <hgoe/nodes/entity_node.h>
#include <hgoe/nodes/document_node.h>
#include <hgoe/edges/document_edge.h>
#include <hgoe/edges/contained_in_edge.h>

int main(int argc, char **argv) {
    std::cout << std::boolalpha;

    std::cout << "==> Testing Hypergraph" << std::endl;
    Hypergraph hgWrite = Hypergraph();

    boost::shared_ptr<Node> n1 = hgWrite.getOrCreateNode(boost::make_shared<DocumentNode>("n1"));
    boost::shared_ptr<Node> n2 = hgWrite.getOrCreateNode(boost::make_shared<TermNode>("n2"));
    boost::shared_ptr<Node> n3 = hgWrite.getOrCreateNode(boost::make_shared<EntityNode>("n3"));

    boost::shared_ptr<Edge> e1 = boost::make_shared<DocumentEdge>("doc_1", NodeSet({n1, n2}), NodeSet({n3}));
    hgWrite.createEdge(e1);

//    std::cout << "In edge: " << (*e1) << std::endl;
//    std::cout << "In edge hash: " << e1->doHash() << std::endl;

    boost::filesystem::path tmpDirPath = boost::filesystem::temp_directory_path() / boost::filesystem::path("army-ant");
    boost::filesystem::create_directories(tmpDirPath);
    boost::filesystem::path tmpPath = tmpDirPath / boost::filesystem::unique_path();

    //std::cout << "\tSaving to " << tmpPath << std::endl;
    hgWrite.save(tmpPath.native());

    //std::cout << "\tLoading from " << tmpPath << std::endl;
    Hypergraph hgLoad = Hypergraph::load(tmpPath.native());

    const NodeSet &nodes = hgLoad.getNodes();

    if (nodes.find(boost::make_shared<DocumentNode>("n1")) == nodes.end()) return 1;
    if (nodes.find(boost::make_shared<TermNode>("n2")) == nodes.end()) return 1;
    if (nodes.find(boost::make_shared<EntityNode>("n3")) == nodes.end()) return 1;

    const EdgeSet &edges = hgLoad.getEdges();
    /*for (const auto &edgeIt : edges) {
        std::cout << "Edge: " << (*edgeIt) << std::endl;
        std::cout << "Edge hash: " << edgeIt->doHash() << std::endl;
    }*/
    boost::shared_ptr<Edge> edge = boost::make_shared<DocumentEdge>(
            "doc_1",
            NodeSet({boost::make_shared<DocumentNode>("n1"), boost::make_shared<TermNode>("n2")}),
            NodeSet({boost::make_shared<EntityNode>("n3")}));
//    std::cout << "Out edge: " << (*edge) << std::endl;
//    std::cout << "Out edge hash: " << edge->doHash() << std::endl;
    if (hgLoad.getEdges().find(edge) == hgLoad.getEdges().end()) return 1;

    return 0;
}