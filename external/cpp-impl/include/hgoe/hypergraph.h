//
// Created by jldevezas on 3/6/18.
//

#ifndef ARMYANT_HYPERGRAPH_H
#define ARMYANT_HYPERGRAPH_H

#include <string>
#include <boost/unordered_set.hpp>
#include <hgoe/nodes/node.h>
#include <boost/python/object.hpp>
#include <hgoe/edges/edge.h>
#include <boost/serialization/access.hpp>
#include <boost/archive/binary_oarchive.hpp>
#include <boost/archive/binary_iarchive.hpp>
#include <boost/serialization/boost_unordered_set.hpp>
#include <boost/serialization/shared_ptr.hpp>

class Hypergraph {
private:
    friend class boost::serialization::access;

    template<class Archive>
    void serialize(Archive &ar, const unsigned int version) {
        ar & nodes;
        ar & edges;
    };

    NodeSet nodes;
    EdgeSet edges;
public:
    boost::shared_ptr<Node> getOrCreateNode(boost::shared_ptr<Node> node);

    unsigned long nodeCount();

    unsigned long edgeCount();

    const NodeSet &getNodes() const;

    boost::shared_ptr<Edge> createEdge(boost::shared_ptr<Edge> edge);

    const EdgeSet &getEdges() const;

    void save(std::string path);

    static Hypergraph load(std::string path);
};

BOOST_CLASS_EXPORT_KEY(Hypergraph)

#endif //ARMYANT_HYPERGRAPH_H
