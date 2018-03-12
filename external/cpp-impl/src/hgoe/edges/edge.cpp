//
// Created by jldevezas on 3/7/18.
//

#include <iostream>

#include <hgoe/edges/edge.h>

BOOST_CLASS_EXPORT_IMPLEMENT(Edge)

unsigned int Edge::nextEdgeID = 0;

Edge::Edge() = default;

Edge::Edge(std::set<Node *, NodeComp> nodes) : Edge(std::move(nodes), std::set<Node *, NodeComp>()) {

}

Edge::Edge(std::set<Node *, NodeComp> tail, std::set<Node *, NodeComp> head) {
    this->edgeID = nextEdgeID++;
    this->tail = std::move(tail);
    this->head = std::move(head);
}

bool Edge::operator<(const Edge &rhs) const {
    if (tail < rhs.tail && head < rhs.head)
        return true;
    return false;
}

bool Edge::operator>(const Edge &rhs) const {
    if (tail > rhs.tail && head > rhs.head)
        return true;
    return false;
}

bool Edge::operator<=(const Edge &rhs) const {
    return !(rhs < *this);
}

bool Edge::operator>=(const Edge &rhs) const {
    return !(*this < rhs);
}

/*bool Edge::operator==(const Edge &rhs) const {
    return tail == rhs.tail &&
           head == rhs.head;
}

bool Edge::operator!=(const Edge &rhs) const {
    return !(rhs == *this);
}*/

unsigned int Edge::getEdgeID() const {
    return edgeID;
}

void Edge::setEdgeID(unsigned int edgeID) {
    Edge::edgeID = edgeID;
}

const std::set<Node *, NodeComp> &Edge::getTail() const {
    return tail;
}

void Edge::setTail(const std::set<Node *, NodeComp> &tail) {
    Edge::tail = tail;
}

const std::set<Node *, NodeComp> &Edge::getHead() const {
    return head;
}

void Edge::setHead(const std::set<Node *, NodeComp> &head) {
    Edge::head = head;
}

const std::set<Node *, NodeComp> &Edge::getNodes() const {
    return getTail();
}

void Edge::setNodes(const std::set<Node *, NodeComp> &nodes) {
    setTail(tail);
}

bool Edge::isDirected() {
    return !this->head.empty();
}
