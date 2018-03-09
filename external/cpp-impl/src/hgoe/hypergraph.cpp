//
// Created by jldevezas on 3/6/18.
//

#include <fstream>
#include <hgoe/hypergraph.h>

BOOST_CLASS_EXPORT_IMPLEMENT(Hypergraph)

Node *Hypergraph::getOrCreateNode(Node *node) {
    if (Hypergraph::nodes.insert(node).second) {
        return node;
    }

    return *nodes.find(node);
}

const std::set<Node *> &Hypergraph::getNodes() const {
    return nodes;
}

Edge *Hypergraph::createEdge(Edge *edge) {
    Hypergraph::edges.insert(edge);
    return edge;
}

const std::set<Edge *> &Hypergraph::getEdges() const {
    return edges;
}

void Hypergraph::save(std::string path) {
    std::ofstream ofs(path);
    boost::archive::binary_oarchive oa(ofs);
    oa << this;
    ofs.close();
}

Hypergraph Hypergraph::load(std::string path) {
    Hypergraph *hg;
    std::ifstream ifs(path);
    boost::archive::binary_iarchive ia(ifs);
    ia >> hg;
    ifs.close();
    return *hg;
}

unsigned long Hypergraph::nodeCount() {
    return nodes.size();
}

unsigned long Hypergraph::edgeCount() {
    return edges.size();
}
