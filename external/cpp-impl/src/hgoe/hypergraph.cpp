//
// Created by jldevezas on 3/6/18.
//

#include <hgoe/hypergraph.h>
#include <iostream>
#include <fstream>

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

std::set<Node>::iterator Hypergraph::findNode(Node node) {
    return nodes.find(node);
}

std::set<Node>::iterator Hypergraph::beginNode() {
    return nodes.begin();
}

std::set<Node>::iterator Hypergraph::endNode() {
    return nodes.end();
}

void Hypergraph::save(std::string path) {
    std::ofstream ofs(path);
    boost::archive::binary_oarchive oa(ofs);
    oa << this;
}

Hypergraph Hypergraph::load(std::string path) {
    Hypergraph hg;
    std::ifstream ifs(path);
    boost::archive::binary_iarchive ia(ifs);
    ia >> hg;
    return hg;
}