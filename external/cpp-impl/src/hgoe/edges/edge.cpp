//
// Created by jldevezas on 3/7/18.
//

#include <iostream>

#include <hgoe/edges/edge.h>

BOOST_CLASS_EXPORT_IMPLEMENT(Edge)

unsigned int Edge::nextEdgeID = 0;

Edge::Edge() = default;

Edge::Edge(std::set<Node *> nodes) : Edge(std::move(nodes), std::set<Node *>()) {

}

Edge::Edge(std::set<Node *> tail, std::set<Node *> head) {
    this->edgeID = nextEdgeID++;
    this->tail = std::move(tail);
    this->head = std::move(head);
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

const std::set<Node *> &Edge::getTail() const {
    return tail;
}

void Edge::setTail(const std::set<Node *> &tail) {
    Edge::tail = tail;
}

const std::set<Node *> &Edge::getHead() const {
    return head;
}

void Edge::setHead(const std::set<Node *> &head) {
    Edge::head = head;
}

const std::set<Node *> &Edge::getNodes() const {
    return getTail();
}

void Edge::setNodes(const std::set<Node *> &nodes) {
    setTail(tail);
}

bool Edge::isDirected() {
    return !this->head.empty();
}

bool Edge::operator==(const Edge &rhs) const {
    return tail == rhs.tail &&
           head == rhs.head;
}

bool Edge::operator!=(const Edge &rhs) const {
    return !(rhs == *this);
}
