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

std::size_t Edge::doHash() const {
    std::size_t h = 0;
    boost::hash_combine(h, label());
    boost::hash_combine(h, tail);
    boost::hash_combine(h, head);
    return h;
}

void Edge::print(std::ostream &os) const {
    os << "Edge { edgeID: " << edgeID << ", tail: " << tail << ", head: " << head << " }";
}

std::ostream &operator<<(std::ostream &os, const Edge &edge) {
    edge.print(os);
    return os;
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