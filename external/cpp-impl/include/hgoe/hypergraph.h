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
#include <boost/archive/binary_oarchive.hpp>
#include <boost/archive/binary_iarchive.hpp>
#include <boost/serialization/set.hpp>

class Hypergraph {
private:
    friend class boost::serialization::access;

    template<class Archive>
    void serialize(Archive &ar, const unsigned int version) {
        ar & nodes;
        ar & edges;
    };

    std::set<Node> nodes;
    std::set<Edge> edges;
public:
    Node getOrCreateNode(Node node);

    std::set<Node>::iterator findNode(Node node);

    std::set<Node>::iterator beginNode();

    std::set<Node>::iterator endNode();

    const std::set<Node> &getNodes() const;

    Edge createEdge(Edge edge);

    const std::set<Edge> &getEdges() const;

    void save(std::string path);

    static Hypergraph load(std::string path);
};

#endif //ARMYANT_HYPERGRAPH_H
