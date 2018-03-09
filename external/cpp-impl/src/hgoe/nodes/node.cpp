//
// Created by jldevezas on 3/6/18.
//

#include <hgoe/nodes/node.h>

BOOST_CLASS_EXPORT_IMPLEMENT(Node)

unsigned int Node::nextNodeID = 0;

Node::Node() {
    Node::nodeID = nextNodeID++;
}

Node::Node(std::string name) {
    Node::nodeID = nextNodeID++;
    Node::name = std::move(name);
}

const std::string &Node::getName() const {
    return name;
}

void Node::setName(const std::string &name) {
    Node::name = name;
}

bool Node::operator<(const Node &rhs) const {
    return name < rhs.name;
}

bool Node::operator>(const Node &rhs) const {
    return rhs.name < name;
}

bool Node::operator<=(const Node &rhs) const {
    return !(rhs.name < name);
}

bool Node::operator>=(const Node &rhs) const {
    return !(name < rhs.name);
}

NodeLabel Node::label() {
    return NodeLabel::DEFAULT;
}

unsigned int Node::getNodeID() const {
    return nodeID;
}

void Node::setNodeID(unsigned int nodeID) {
    Node::nodeID = nodeID;
}
