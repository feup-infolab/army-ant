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
#include <hgoe/edges/contained_in_edge.h>

int main(int argc, char **argv) {
    std::cout << std::boolalpha;

    std::cout << "==> Testing Hypergraph" << std::endl;
    Hypergraph hgWrite = Hypergraph();

    boost::shared_ptr<Node> n1 = hgWrite.getOrCreateNode(boost::shared_ptr<Node>(new DocumentNode("n1")));
    boost::shared_ptr<Node> n2 = hgWrite.getOrCreateNode(boost::shared_ptr<Node>(new TermNode("n2")));
    boost::shared_ptr<Node> n3 = hgWrite.getOrCreateNode(boost::shared_ptr<Node>(new EntityNode("n3")));

    boost::shared_ptr<Edge> e1 = boost::shared_ptr<Edge>(new DocumentEdge(NodeSet({n1, n2}), NodeSet({n3})));
    hgWrite.createEdge(e1);

    boost::filesystem::path tmpDirPath = boost::filesystem::temp_directory_path() / boost::filesystem::path("army-ant");
    boost::filesystem::create_directories(tmpDirPath);
    boost::filesystem::path tmpPath = tmpDirPath / boost::filesystem::unique_path();

    std::cout << "\tSaving to " << tmpPath << std::endl;
    hgWrite.save(tmpPath.native());

    std::cout << "\tLoading from " << tmpPath << std::endl;
    Hypergraph hgLoad = Hypergraph::load(tmpPath.native());

    const NodeSet &nodes = hgLoad.getNodes();

    boost::shared_ptr<Node> node1 = boost::shared_ptr<Node>(new DocumentNode("n0"));
    boost::shared_ptr<Node> node2 = boost::shared_ptr<Node>(new DocumentNode("n0"));
    std::cout << "node1 == node2: " << (node1 == node2) << std::endl;
    std::cout << "*node1 == *node2: " << (*node1 == *node2) << std::endl;

    std::cout << "node1 in hgLoad: " << (nodes.find(node1) != nodes.end()) << std::endl;

    if (nodes.find(boost::shared_ptr<Node>(new DocumentNode("n1"))) == nodes.end()) return 1;
    if (nodes.find(boost::shared_ptr<Node>(new TermNode("n2"))) == nodes.end()) return 1;
    if (nodes.find(boost::shared_ptr<Node>(new EntityNode("n3"))) == nodes.end()) return 1;

    boost::shared_ptr<Edge> edge1 = boost::shared_ptr<Edge>(
            new DocumentEdge(NodeSet({boost::shared_ptr<Node>(new DocumentNode("n0")),
                                      boost::shared_ptr<Node>(new TermNode("n1"))}),
                             NodeSet({boost::shared_ptr<Node>(new EntityNode("n2"))})));
    boost::shared_ptr<Edge> edge2 = boost::shared_ptr<Edge>(
            new DocumentEdge(NodeSet({boost::shared_ptr<Node>(new DocumentNode("n0")),
                                      boost::shared_ptr<Node>(new TermNode("n1"))}),
                             NodeSet({boost::shared_ptr<Node>(new EntityNode("n2"))})));
    std::cout << "*edge1 == *edge2: " << (*edge1 == *edge2) << std::endl;

    const EdgeSet &edges = hgLoad.getEdges();
    boost::shared_ptr<Edge> edge = boost::shared_ptr<Edge>(
            new DocumentEdge(NodeSet({boost::shared_ptr<Node>(new DocumentNode("n1")),
                                      boost::shared_ptr<Node>(new TermNode("n2"))}),
                             NodeSet({boost::shared_ptr<Node>(new EntityNode("n3"))})));
    if (hgLoad.getEdges().find(edge) == hgLoad.getEdges().end())
        return 1;

    return 0;
}