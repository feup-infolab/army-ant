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
    Node::name = boost::move(name);
}

const std::string &Node::getName() const {
    return name;
}

void Node::setName(const std::string &name) {
    Node::name = name;
}

bool Node::operator==(const Node &rhs) const {
    return label() == rhs.label() && name == rhs.name;
}

bool Node::operator!=(const Node &rhs) const {
    return !(rhs == *this);
}

void Node::print(std::ostream &os) const {
    os << "{ nodeID: " << nodeID << ", name: " << name << " }";
}

std::ostream &operator<<(std::ostream &os, const Node &node) {
    node.print(os);
    return os;
}

Node::Label Node::label() const {
    return Label::DEFAULT;
}

unsigned int Node::getNodeID() const {
    return nodeID;
}

void Node::setNodeID(unsigned int nodeID) {
    Node::nodeID = nodeID;
}

std::size_t hash_value(const Node &node) {
    boost::hash<Node::Label> labelHash;
    boost::hash<std::string> strHash;
    size_t h = 0;
    boost::hash_combine(h, labelHash(node.label()));
    boost::hash_combine(h, strHash(node.getName()));
    return h;
}