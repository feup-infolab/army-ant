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

int testNodeCompare() {
    std::cout << "\n==> Testing Node compare" << std::endl;
    boost::shared_ptr<Node> node1 = boost::make_shared<DocumentNode>("n1");
    boost::shared_ptr<Node> node2 = boost::make_shared<DocumentNode>("n1");
    std::cout << "node1 == node2: " << (node1 == node2) << std::endl;
    std::cout << "*node1 == *node2: " << (*node1 == *node2) << std::endl;
    if (*node1 == *node2) return 0;
    return 1;
}

int testNodeSetCompare() {
    std::cout << "\n==> Testing NodeSet compare" << std::endl;
    NodeSet nodeSet1({boost::make_shared<DocumentNode>("n1"), boost::make_shared<TermNode>("n2")});
    NodeSet nodeSet2({boost::make_shared<DocumentNode>("n1"), boost::make_shared<TermNode>("n2")});
    std::cout << "nodeSet1 == nodeSet2: " << (nodeSet1 == nodeSet2) << std::endl;
    if (nodeSet1 == nodeSet2) return 0;
    return 1;
}

int main(int argc, char **argv) {
    std::cout << std::boolalpha;

    int ret;

    if ( (ret = testNodeCompare()) != 0) return ret;
    if ( (ret = testNodeSetCompare()) != 0) return ret;

    return 0;
}