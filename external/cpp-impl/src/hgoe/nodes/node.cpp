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
    return label() < rhs.label() && name < rhs.name;
}

bool Node::operator>(const Node &rhs) const {
    return label() > rhs.label() && name > rhs.name;
}

bool Node::operator<=(const Node &rhs) const {
    return !(rhs < *this);
}

bool Node::operator>=(const Node &rhs) const {
    return !(*this < rhs);
}

bool Node::operator==(const Node &rhs) const {
    return label() == rhs.label() && name == rhs.name;
}

bool Node::operator!=(const Node &rhs) const {
    return !(rhs == *this);
}

NodeLabel Node::label() const {
    return NodeLabel::DEFAULT;
}

unsigned int Node::getNodeID() const {
    return nodeID;
}

void Node::setNodeID(unsigned int nodeID) {
    Node::nodeID = nodeID;
}

bool NodeComp::operator()(const Node *lhs, const Node *rhs) const {
    return *lhs < *rhs;
}