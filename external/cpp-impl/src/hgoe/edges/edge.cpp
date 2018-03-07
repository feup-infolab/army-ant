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
