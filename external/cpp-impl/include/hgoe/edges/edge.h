//
// Created by jldevezas on 3/7/18.
//

#ifndef ARMY_ANT_CPP_EDGE_H
#define ARMY_ANT_CPP_EDGE_H

#include <boost/unordered_set.hpp>

#include <hgoe/nodes/node.h>
#include <boost/archive/binary_oarchive.hpp>
#include <boost/archive/binary_iarchive.hpp>
#include <boost/serialization/boost_unordered_set.hpp>
#include <boost/serialization/shared_ptr.hpp>
#include <boost/serialization/export.hpp>

class Edge {
private:
    friend class boost::serialization::access;

    template<class Archive>
    void serialize(Archive &ar, unsigned int version) {
        ar & edgeID;
        ar & tail;
        ar & head;
    };

    unsigned int edgeID;
    NodeSet tail;
    NodeSet head;
protected:
    static unsigned int nextEdgeID;
public:
    enum EdgeLabel {
        DEFAULT = 0,
        DOCUMENT = 1,
        RELATED_TO = 2,
        CONTAINED_IN = 3
    };

    Edge();

    explicit Edge(NodeSet nodes);

    Edge(NodeSet tail, NodeSet head);

    /*bool operator<(const Edge &rhs) const;

    bool operator>(const Edge &rhs) const;

    bool operator<=(const Edge &rhs) const;

    bool operator>=(const Edge &rhs) const;*/

    bool operator==(const Edge &rhs) const;

    bool operator!=(const Edge &rhs) const;

    unsigned int getEdgeID() const;

    void setEdgeID(unsigned int edgeID);

    const NodeSet &getTail() const;

    void setTail(const NodeSet &tail);

    const NodeSet &getHead() const;

    void setHead(const NodeSet &head);

    const NodeSet &getNodes() const;

    void setNodes(const NodeSet &nodes);

    bool isDirected();

    virtual EdgeLabel label() const = 0;
};

typedef boost::unordered_set<boost::shared_ptr<Edge>> EdgeSet;

BOOST_SERIALIZATION_ASSUME_ABSTRACT(Edge)
BOOST_CLASS_EXPORT_KEY(Edge)

#endif //ARMY_ANT_CPP_EDGE_H