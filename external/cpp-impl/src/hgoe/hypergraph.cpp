//
// Created by jldevezas on 3/6/18.
//

#include <fstream>

#include <hgoe/hypergraph.h>

BOOST_CLASS_EXPORT_IMPLEMENT(Hypergraph)

boost::shared_ptr<Node> Hypergraph::getOrCreateNode(boost::shared_ptr<Node> node) {
    if (Hypergraph::nodes.insert(node).second) {
        return node;
    }

    return *nodes.find(node);
}

const NodeSet &Hypergraph::getNodes() const {
    return nodes;
}

boost::shared_ptr<Edge> Hypergraph::createEdge(boost::shared_ptr<Edge> edge) {
    Hypergraph::edges.insert(edge);
    if (edge->isDirected()) {
        for (auto nodeIt : edge->getTail()) {
            adjacencyList[nodeIt]->insert(edge);
        }
    } else {
        for (auto nodeIt : edge->getNodes()) {
            adjacencyList[nodeIt]->insert(edge);
        }
    }
    return edge;
}

const EdgeSet &Hypergraph::getEdges() const {
    return edges;
}

const boost::shared_ptr<EdgeSet> &Hypergraph::getIncidentEdges(boost::shared_ptr<Node> node) const {
    return adjacencyList.at(node);
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
