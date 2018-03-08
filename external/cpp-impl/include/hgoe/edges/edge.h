//
// Created by jldevezas on 3/7/18.
//

#ifndef ARMY_ANT_CPP_EDGE_H
#define ARMY_ANT_CPP_EDGE_H

#include <set>
#include <hgoe/nodes/node.h>

class Edge {
private:
    unsigned int edgeID;
    std::set<Node> tail;
    std::set<Node> head;
protected:
    static unsigned int nextEdgeID;
public:
    Edge();

    Edge(std::set <Node> nodes);

    Edge(std::set<Node> tail, std::set<Node> head);

    bool operator<(const Edge &rhs) const;

    bool operator>(const Edge &rhs) const;

    bool operator<=(const Edge &rhs) const;

    bool operator>=(const Edge &rhs) const;

    unsigned int getEdgeID() const;

    void setEdgeID(unsigned int edgeID);

    const std::set<Node> &getTail() const;

    void setTail(const std::set<Node> &tail);

    const std::set<Node> &getHead() const;

    void setHead(const std::set<Node> &head);

    bool isDirected();
};

#endif //ARMY_ANT_CPP_EDGE_H