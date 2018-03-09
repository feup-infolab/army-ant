//
// Created by jldevezas on 3/5/18.
//

#include <iostream>
#include <hgoe/hypergraph.h>
#include <boost/filesystem.hpp>
#include <hgoe/nodes/term_node.h>
#include <hgoe/nodes/entity_node.h>
#include <hgoe/nodes/document_node.h>
#include <hgoe/edges/document_edge.h>

int main(int argc, char **argv) {
    std::cout << "==> Testing Hypergraph" << std::endl;
    Hypergraph hgWrite = Hypergraph();

    Node *n1 = hgWrite.getOrCreateNode(new DocumentNode("n1"));
    Node *n2 = hgWrite.getOrCreateNode(new TermNode("n2"));
    Node *n3 = hgWrite.getOrCreateNode(new EntityNode("n3"));

    Edge *e1 = new DocumentEdge({n1, n2}, {n3});
    hgWrite.createEdge(e1);

    boost::filesystem::path tmpDirPath = boost::filesystem::temp_directory_path() / boost::filesystem::path("army-ant");
    boost::filesystem::create_directories(tmpDirPath);
    boost::filesystem::path tmpPath = tmpDirPath / boost::filesystem::unique_path();

    std::cout << "\tSaving to " << tmpPath << std::endl;
    hgWrite.save(tmpPath.native());

    std::cout << "\tLoading from " << tmpPath << std::endl;
    Hypergraph hgLoad = Hypergraph::load(tmpPath.native());

    const std::set<Node *> &nodes = hgLoad.getNodes();

    for (auto node : nodes) {
        if (node == new DocumentNode("n1")) {
            std::cout << node->getName() << std::endl;
        }
    }

    //std::cout << (*nodes.find(new DocumentNode("n1")))->getName() << std::endl;

    if (nodes.find(new DocumentNode("n1")) == nodes.end()) return 1;
    if (nodes.find(new TermNode("n2")) == nodes.end()) return 1;
    if (nodes.find(new EntityNode("n3")) == nodes.end()) return 1;

    const std::set<Edge *> &edges = hgLoad.getEdges();
    if (hgLoad.getEdges().find(e1) == hgLoad.getEdges().end()) return 1;

    return 0;

    /*auto n0 = new DocumentNode("n0");
    auto n1 = new TermNode("n1");
    auto n2 = new EntityNode("n2");

    std::set<Node *> tail = {n0};
    std::set<Node *> head = {n1, n2};

    Edge *e0 = new DocumentEdge(tail, head);
    e0->setEdgeID(10);

    std::cout << "In: " << e0->getHead().size() << std::endl;

    std::ofstream ofs("/tmp/edge");
    boost::archive::binary_oarchive oa(ofs);
    oa << e0;
    ofs.close();

    Edge *edge;
    std::ifstream ifs("/tmp/edge");
    boost::archive::binary_iarchive ia(ifs);
    ia >> edge;
    ifs.close();

    std::cout << "Out: " << edge->getHead().size() << std::endl;*/
}