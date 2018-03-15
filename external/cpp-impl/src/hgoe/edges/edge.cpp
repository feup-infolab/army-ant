//
// Created by jldevezas on 3/7/18.
//

#include <iostream>

#include <hgoe/nodes/node_set.h>
#include <hgoe/edges/edge.h>

BOOST_CLASS_EXPORT_IMPLEMENT(Edge)

unsigned int Edge::nextEdgeID = 0;

Edge::Edge() = default;

Edge::Edge(NodeSet nodes) : Edge(boost::move(nodes), NodeSet()) {}

Edge::Edge(NodeSet tail, NodeSet head) {
    this->edgeID = nextEdgeID++;
    this->tail = boost::move(tail);
    this->head = boost::move(head);
}

bool Edge::doCompare(const Edge &rhs) const {
    return true;
}

bool Edge::operator==(const Edge &rhs) const {
    return label() == rhs.label()
           && doCompare(rhs)
           && tail == rhs.tail
           && head == rhs.head;
}

bool Edge::operator!=(const Edge &rhs) const {
    return !(rhs == *this);
}

unsigned int Edge::getEdgeID() const {
    return edgeID;
}

void Edge::setEdgeID(unsigned int edgeID) {
    Edge::edgeID = edgeID;
}

const NodeSet &Edge::getTail() const {
    return tail;
}

void Edge::setTail(const NodeSet &tail) {
    Edge::tail = tail;
}

const NodeSet &Edge::getHead() const {
    return head;
}

void Edge::setHead(const NodeSet &head) {
    Edge::head = head;
}

const NodeSet &Edge::getNodes() const {
    return getTail();
}

void Edge::setNodes(const NodeSet &nodes) {
    setTail(tail);
}

bool Edge::isDirected() {
    return !this->head.empty();
}

bool Edge::Equal::operator()(const boost::shared_ptr<Edge> &lhs, const boost::shared_ptr<Edge> &rhs) const {
    return *lhs == *rhs;
}

std::size_t Edge::Hash::operator()(const boost::shared_ptr<Edge> &edge) const {
    boost::hash<Edge::EdgeLabel> labelHasher;
    boost::hash<NodeSet> nodeSetHasher;
    std::size_t h = 0;
    boost::hash_combine(h, labelHasher(edge->label()));
    boost::hash_combine(h, nodeSetHasher(edge->tail));
    boost::hash_combine(h, nodeSetHasher(edge->head));
    return h;
}