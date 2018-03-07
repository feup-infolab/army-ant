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
};

#endif //ARMY_ANT_CPP_EDGE_H