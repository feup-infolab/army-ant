//
// Created by jldevezas on 3/6/18.
//

#include <hypergraph.h>
#include <iostream>
#include <boost/python/extract.hpp>

Node Hypergraph::getOrCreateNode(Node node) {
    Hypergraph::nodes.insert(node);
}

const std::set<Node> &Hypergraph::getNodes() const {
    return nodes;
}
