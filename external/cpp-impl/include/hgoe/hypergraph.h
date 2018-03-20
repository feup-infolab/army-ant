//
// Created by jldevezas on 3/6/18.
//

#ifndef ARMYANT_HYPERGRAPH_H
#define ARMYANT_HYPERGRAPH_H

#include <string>

#include <boost/unordered_set.hpp>
#include <boost/container/vector.hpp>
#include <boost/unordered_map.hpp>
#include <boost/python/object.hpp>
#include <boost/serialization/access.hpp>
#include <boost/serialization/boost_unordered_set.hpp>
#include <boost/serialization/shared_ptr.hpp>
#include <boost/archive/binary_oarchive.hpp>
#include <boost/archive/binary_iarchive.hpp>

#include <hgoe/nodes/node.h>
#include <hgoe/edges/edge.h>
#include <hgoe/edges/edge_set.h>

// TODO Should also include edges, so we know which edge was traversed.
typedef boost::container::vector<boost::shared_ptr<Node>> Path;
typedef boost::unordered_map<boost::shared_ptr<Node>, boost::shared_ptr<EdgeSet>, NodeHash, NodeEqual> AdjacencyList;

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
    AdjacencyList outEdges;
    AdjacencyList inEdges;
public:
    boost::shared_ptr<Node> getOrCreateNode(boost::shared_ptr<Node> node);

    unsigned long nodeCount();

    unsigned long edgeCount();

    const NodeSet &getNodes() const;

    boost::shared_ptr<Edge> createEdge(boost::shared_ptr<Edge> edge);

    const EdgeSet &getEdges() const;

    EdgeSet getOutEdges(boost::shared_ptr<Node> node);

    EdgeSet getInEdges(boost::shared_ptr<Node> node);

    const EdgeSet getAllEdges(boost::shared_ptr<Node> node) const;

    void save(std::string path);

    static Hypergraph load(std::string path);
};

BOOST_CLASS_EXPORT_KEY(Hypergraph)

#endif //ARMYANT_HYPERGRAPH_H
