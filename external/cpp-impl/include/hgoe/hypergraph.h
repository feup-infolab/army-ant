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
#include <boost/serialization/access.hpp>
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

    // FIXME estes sets precisam de um comparador por valor para isto tudo funcionar!
    std::set<Node *> nodes;
    std::set<Edge *> edges;
public:
    Node *getOrCreateNode(Node *node);

    unsigned long nodeCount();

    unsigned long edgeCount();

    const std::set<Node *> &getNodes() const;

    Edge* createEdge(Edge *edge);

    const std::set<Edge *> &getEdges() const;

    void save(std::string path);

    static Hypergraph load(std::string path);
};

BOOST_CLASS_EXPORT_KEY(Hypergraph)

#endif //ARMYANT_HYPERGRAPH_H
