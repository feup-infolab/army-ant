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

std::ostream &operator<<(std::ostream &os, const Node &node) {
    os << "{ nodeID: " << node.nodeID << ", name: " << node.name << " }";
    return os;
}

Node::NodeLabel Node::label() const {
    return NodeLabel::DEFAULT;
}

unsigned int Node::getNodeID() const {
    return nodeID;
}

void Node::setNodeID(unsigned int nodeID) {
    Node::nodeID = nodeID;
}

const EdgeSet &Node::getOutEdges() const {
    return outEdges;
}

void Node::addOutEdge(boost::shared_ptr<Edge> outEdge) {
    Node::outEdges.insert(outEdge);
}

void Node::addOutEdges(EdgeSet outEdges) {
    Node::outEdges.insert(outEdges.begin(), outEdges.end());
}

const EdgeSet &Node::getInEdges() const {
    return inEdges;
}

void Node::addInEdge(boost::shared_ptr<Edge> inEdge) {
    Node::inEdges.insert(inEdge);
}

void Node::addInEdges(EdgeSet inEdges) {
    Node::inEdges.insert(inEdges.begin(), inEdges.end());
}

std::size_t hash_value(const Node &node) {
    boost::hash<Node::NodeLabel> labelHash;
    boost::hash<std::string> strHash;
    size_t h = 0;
    boost::hash_combine(h, labelHash(node.label()));
    boost::hash_combine(h, strHash(node.getName()));
    return h;
}