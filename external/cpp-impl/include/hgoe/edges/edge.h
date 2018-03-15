//
// Created by jldevezas on 3/7/18.
//

#ifndef ARMY_ANT_CPP_EDGE_H
#define ARMY_ANT_CPP_EDGE_H

#include <ostream>

#include <boost/unordered_set.hpp>
#include <boost/archive/binary_oarchive.hpp>
#include <boost/archive/binary_iarchive.hpp>
#include <boost/serialization/boost_unordered_set.hpp>
#include <boost/serialization/shared_ptr.hpp>
#include <boost/serialization/export.hpp>

#include <hgoe/nodes/node.h>
#include <hgoe/nodes/node_set.h>

class Edge {
private:
    friend class boost::serialization::access;

    template<class Archive>
    void serialize(Archive &ar, unsigned int version) {
        ar & edgeID;
        ar & tail;
        ar & head;
    };
protected:
    static unsigned int nextEdgeID;

    unsigned int edgeID;
    NodeSet tail;
    NodeSet head;
public:
    enum EdgeLabel {
        DEFAULT = 0,
        DOCUMENT = 1,
        RELATED_TO = 2,
        CONTAINED_IN = 3
    };

    struct Equal {
        bool operator()(const boost::shared_ptr<Edge> &lhs, const boost::shared_ptr<Edge> &rhs) const;
    };

    struct Hash {
        std::size_t operator()(const boost::shared_ptr<Edge> &edge) const;
    };

    Edge();

    explicit Edge(NodeSet nodes);

    Edge(NodeSet tail, NodeSet head);

    virtual bool doCompare(const Edge &rhs) const;

    bool operator==(const Edge &rhs) const;

    bool operator!=(const Edge &rhs) const;

    virtual std::size_t doHash() const;

    virtual void print(std::ostream &os) const;

    friend std::ostream &operator<<(std::ostream &os, const Edge &edge);

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

std::size_t hash_value(const Edge &edge);

BOOST_SERIALIZATION_ASSUME_ABSTRACT(Edge)
BOOST_CLASS_EXPORT_KEY(Edge)

#endif //ARMY_ANT_CPP_EDGE_H