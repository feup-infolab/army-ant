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

int testEdgeCompare() {
    std::cout << "\n==> Testing Edge compare" << std::endl;

    boost::shared_ptr<Edge> edge1 = boost::make_shared<DocumentEdge>(
            NodeSet({boost::make_shared<DocumentNode>("n0"), boost::make_shared<TermNode>("n1")}),
            NodeSet({boost::make_shared<EntityNode>("n2")}));

    boost::shared_ptr<Edge> edge2 = boost::make_shared<DocumentEdge>(
            NodeSet({boost::make_shared<DocumentNode>("n0"), boost::make_shared<TermNode>("n1")}),
            NodeSet({boost::make_shared<EntityNode>("n2")}));

    std::cout << "*edge1 == *edge2: " << (*edge1 == *edge2) << std::endl;
    if (*edge1 == *edge2) return 0;
    return 1;
}

int testEdgeSetCompare() {
    std::cout << "\n==> Testing EdgeSet compare" << std::endl;

    auto n1 = boost::make_shared<DocumentNode>("n1");
    auto n2 = boost::make_shared<TermNode>("n2");
    auto n3 = boost::make_shared<EntityNode>("n3");

    NodeSet nodeSet1({n1, n2});
    NodeSet nodeSet2({n3});

    auto edge1a = boost::make_shared<DocumentEdge>("doc_1", nodeSet1, nodeSet2);
    auto edge1b = boost::make_shared<DocumentEdge>("doc_1", nodeSet1, nodeSet2);

    std::cout << "*edge1a == *edge1b: " << (*edge1a == *edge1b) << std::endl;

    EdgeSet edgeSet1 = EdgeSet({edge1a});
    EdgeSet edgeSet2 = EdgeSet({edge1b});

    std::cout << "edgeSet1 == edgeSet2: " << (edgeSet1 == edgeSet2) << std::endl;

    if (edgeSet1 == edgeSet2) return 0;
    return 1;
}

int main(int argc, char **argv) {
    std::cout << std::boolalpha;

    int ret;

    if ( (ret = testEdgeCompare()) != 0) return ret;
    if ( (ret = testEdgeSetCompare()) != 0) return ret;
    
    return 0;
}