//
// Created by jldevezas on 3/7/18.
//

#include <iostream>

#include <hgoe/edges/edge.h>
#include <boost/functional/hash.hpp>

BOOST_CLASS_EXPORT_IMPLEMENT(Edge)

unsigned int Edge::nextEdgeID = 0;

Edge::Edge() = default;

Edge::Edge(NodeSet nodes) : Edge(boost::move(nodes), NodeSet()) {}

Edge::Edge(NodeSet tail, NodeSet head) {
    this->edgeID = nextEdgeID++;
    this->tail = boost::move(tail);
    this->head = boost::move(head);
}

/*bool Edge::operator<(const Edge &rhs) const {
    if (label() > rhs.label())
        return false;

    if (tail.size() > rhs.tail.size())
        return false;

    if (head.size() > rhs.head.size())
        return false;

    bool anyLess = false;

    if (tail.size() == rhs.tail.size()) {
        for (auto lhsIt = tail.begin(), rhsIt = rhs.tail.begin(); lhsIt != tail.end(); lhsIt++, rhsIt++) {
            if (**lhsIt > **rhsIt)
                return false;

            anyLess = anyLess || (**lhsIt < **rhsIt);
        }
    }

    if (head.size() == rhs.head.size()) {
        for (auto lhsIt = head.begin(), rhsIt = rhs.head.begin(); lhsIt != head.end(); lhsIt++, rhsIt++) {
            if (**lhsIt > **rhsIt)
                return false;

            anyLess = anyLess || (**lhsIt < **rhsIt);
        }
    }

    return label() < rhs.label() || tail.size() < rhs.tail.size() || head.size() < rhs.head.size() || anyLess;
}

bool Edge::operator>(const Edge &rhs) const {
    if (label() <= rhs.label())
        return false;

    if (tail.size() <= rhs.tail.size() || head.size() <= rhs.head.size())
        return false;

    for (auto lhsNode = tail.begin(), rhsNode = rhs.tail.begin(); lhsNode != tail.end(); lhsNode++, rhsNode++) {
        if (*lhsNode <= *rhsNode)
            return false;
    }

    for (auto lhsNode = head.begin(), rhsNode = rhs.head.begin(); lhsNode != head.end(); lhsNode++, rhsNode++) {
        if (*lhsNode <= *rhsNode)
            return false;
    }

    return true;
}

bool Edge::operator<=(const Edge &rhs) const {
    return !(rhs < *this);
}

bool Edge::operator>=(const Edge &rhs) const {
    return !(*this < rhs);
}*/

bool Edge::operator==(const Edge &rhs) const {
    if (label() != rhs.label())
        return false;

    if (tail.size() != rhs.tail.size() || head.size() != rhs.head.size())
        return false;

    for (auto lhsNode = tail.begin(), rhsNode = rhs.tail.begin(); lhsNode != tail.end(); lhsNode++, rhsNode++) {
        if (*lhsNode != *rhsNode)
            return false;
    }

    for (auto lhsNode = head.begin(), rhsNode = rhs.head.begin(); lhsNode != head.end(); lhsNode++, rhsNode++) {
        if (*lhsNode != *rhsNode)
            return false;
    }

    return true;
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

/*bool Edge::EdgeEqual::operator()(const boost::shared_ptr<Edge> lhs, const boost::shared_ptr<Edge> rhs) const {
    return *lhs == *rhs;
}*/

/*std::size_t Edge::hash_value(const boost::shared_ptr<Edge> edge) const {
    boost::hash<Edge::EdgeLabel> labelHasher;
    boost::hash<NodeSet> nodeSetHasher;
    std::size_t h = 0;
    boost::hash_combine(h, labelHasher(edge->label()));
    boost::hash_combine(h, nodeSetHasher(edge->tail));
    boost::hash_combine(h, nodeSetHasher(edge->head));
    return h;
}*/
