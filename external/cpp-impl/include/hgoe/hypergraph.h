//
// Created by jldevezas on 3/6/18.
//

#ifndef ARMYANT_HYPERGRAPH_H
#define ARMYANT_HYPERGRAPH_H

#include <string>
#include <set>
#include <hgoe/nodes/node.h>
#include <boost/python/object.hpp>
#include <hgoe/edges/edge.h>

class Hypergraph {
private:
    std::set<Node> nodes;
    std::set<Edge> edges;
public:
    Node getOrCreateNode(Node node);

    const std::set<Node> &getNodes() const;

    Edge createEdge(Edge edge);

    const std::set<Edge> &getEdges() const;
};

#endif //ARMYANT_HYPERGRAPH_H
