//
// Created by jldevezas on 3/6/18.
//

#include <node/node.h>

Node::Node() {
    Node::name = "";
}

Node::Node(std::string name) {
    Node::name = name;
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
    return rhs < *this;
}

bool Node::operator<=(const Node &rhs) const {
    return !(rhs < *this);
}

bool Node::operator>=(const Node &rhs) const {
    return !(*this < rhs);
}
