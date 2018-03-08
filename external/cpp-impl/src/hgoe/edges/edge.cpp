//
// Created by jldevezas on 3/7/18.
//

#include <hgoe/edges/edge.h>

unsigned int Edge::nextEdgeID = 0;

Edge::Edge() {
    this->edgeID = nextEdgeID++;
}

Edge::Edge(std::set<Node> nodes) : Edge() {
    this->tail = nodes;
    this->head = std::set<Node>();
}

Edge::Edge(std::set<Node> tail, std::set<Node> head) {
    this->tail = tail;
    this->head = head;
}

bool Edge::operator<(const Edge &rhs) const {
    if (tail < rhs.tail)
        return true;
    if (rhs.tail < tail)
        return false;
    return head < rhs.head;
}

bool Edge::operator>(const Edge &rhs) const {
    return rhs < *this;
}

bool Edge::operator<=(const Edge &rhs) const {
    return !(rhs < *this);
}

bool Edge::operator>=(const Edge &rhs) const {
    return !(*this < rhs);
}

unsigned int Edge::getEdgeID() const {
    return edgeID;
}

void Edge::setEdgeID(unsigned int edgeID) {
    Edge::edgeID = edgeID;
}

const std::set<Node> &Edge::getTail() const {
    return tail;
}

void Edge::setTail(const std::set<Node> &tail) {
    Edge::tail = tail;
}

const std::set<Node> &Edge::getHead() const {
    return head;
}

void Edge::setHead(const std::set<Node> &head) {
    Edge::head = head;
}

bool Edge::isDirected() {
    return !this->head.empty();
}