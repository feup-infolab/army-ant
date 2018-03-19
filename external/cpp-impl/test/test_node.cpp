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

    auto n1a = boost::make_shared<DocumentNode>("n1");
    auto n2a = boost::make_shared<TermNode>("n2");
    auto n1b = boost::make_shared<DocumentNode>("n1");
    auto n2b = boost::make_shared<TermNode>("n2");

    NodeSet nodeSet1({n1a, n2a});
    NodeSet nodeSet2({n1b, n2b});

    std::cout << "nodeSet1 == nodeSet2: " << (nodeSet1 == nodeSet2) << std::endl;

    if (nodeSet1 == nodeSet2) return 0;
    return 1;
}

int testEntityNodeSerialization() {
    std::cout << "\n==> Testing EntityNode serialization" << std::endl;

    NodeSet outEntityNodes = {
            boost::make_shared<EntityNode>(new Document("doc_1", "entityName", "text", std::vector<Triple>()), "entityName")};
    std::ofstream ofs("/tmp/hgoe-entity-node");
    boost::archive::binary_oarchive oa(ofs);
    oa << outEntityNodes;
    ofs.close();

    NodeSet inEntityNodes;
    std::ifstream ifs("/tmp/hgoe-entity-node");
    boost::archive::binary_iarchive ia(ifs);
    ia >> inEntityNodes;
    ifs.close();

    Node *outNode = outEntityNodes.begin()->get();
    EntityNode *inNode = dynamic_cast<EntityNode *>(inEntityNodes.begin()->get());

    std::cout << "Saved node: " << (*outNode) << std::endl;
    std::cout << "Loaded node: " << (*inNode) << std::endl;

    if (outNode->label() != inNode->label()) return 1;
    if (outNode->getName() != inNode->getName()) return 1;
    if (outNode->getNodeID() != inNode->getNodeID()) return 1;

    return 0;
}

int main(int argc, char **argv) {
    std::cout << std::boolalpha;

    int ret;

    if ((ret = testNodeCompare()) != 0) return ret;
    if ((ret = testNodeSetCompare()) != 0) return ret;
    if ((ret = testEntityNodeSerialization()) != 0) return ret;

    return 0;
}