//
// Created by jldevezas on 3/6/18.
//

#include <hgoe/hypergraph.h>
#include <iostream>

Node Hypergraph::getOrCreateNode(Node node) {
    if (Hypergraph::nodes.insert(node).second) {
        return node;
    }

    return *nodes.find(node);
}

const std::set<Node> &Hypergraph::getNodes() const {
    return nodes;
}

Edge Hypergraph::createEdge(Edge edge) {
    Hypergraph::edges.insert(edge);
    return edge;
}

const std::set<Edge> &Hypergraph::getEdges() const {
    return edges;
}
