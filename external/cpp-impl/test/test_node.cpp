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

struct NEqual : std::binary_function<boost::shared_ptr<int>, boost::shared_ptr<int>, bool> {
    bool operator()(const boost::shared_ptr<int> &lhs, const boost::shared_ptr<int> &rhs) const {
        return *lhs == *rhs;
    };
};

struct NHash : std::unary_function<boost::shared_ptr<int>, std::size_t> {
    std::size_t operator()(const boost::shared_ptr<int> &i) const {
        return boost::hash<int>()(*i);
    }
};

int testNodeSetCompare() {
    std::cout << "\n==> Testing NodeSet compare" << std::endl;

    /*std::cout << "generic set compare: "
              << (boost::unordered_set<boost::shared_ptr<int>, NEqual, NHash, std::allocator<int>>(
                      {boost::make_shared<int>(10), boost::make_shared<int>(20)}) ==
                  boost::unordered_set<boost::shared_ptr<int>, NEqual, NHash, std::allocator<int>>(
                          {boost::make_shared<int>(10), boost::make_shared<int>(20)}))
              << std::endl;*/

    NodeSet nodeSet1({boost::make_shared<DocumentNode>("n1"), boost::make_shared<TermNode>("n2")});
    NodeSet nodeSet2({boost::make_shared<DocumentNode>("n1"), boost::make_shared<TermNode>("n2")});

    std::cout << nodeSet1.size() << std::endl;
    std::cout << (**nodeSet1.begin()) << std::endl;

    std::cout << "nodeSet1 == nodeSet2: " << (nodeSet1 == nodeSet2) << std::endl;

    if (nodeSet1 == nodeSet2) return 0;
    return 1;
}

int main(int argc, char **argv) {
    std::cout << std::boolalpha;

    int ret;

    if ((ret = testNodeCompare()) != 0) return ret;
    if ((ret = testNodeSetCompare()) != 0) return ret;

    return 0;
}