//
// Created by jldevezas on 3/7/18.
//

#ifndef ARMY_ANT_CPP_EDGE_H
#define ARMY_ANT_CPP_EDGE_H

#include <set>
#include <hgoe/nodes/node.h>
#include <boost/archive/binary_oarchive.hpp>
#include <boost/archive/binary_iarchive.hpp>
#include <boost/serialization/set.hpp>
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
    std::set<Node *, NodeComp> tail;
    std::set<Node *, NodeComp> head;
protected:
    static unsigned int nextEdgeID;
public:
    Edge();

    explicit Edge(std::set <Node *, NodeComp> nodes);

    Edge(std::set<Node *, NodeComp> tail, std::set<Node *, NodeComp> head);

    bool operator<(const Edge &rhs) const;

    bool operator>(const Edge &rhs) const;

    bool operator<=(const Edge &rhs) const;

    bool operator>=(const Edge &rhs) const;

    bool operator==(const Edge &rhs) const;

    bool operator!=(const Edge &rhs) const;

    unsigned int getEdgeID() const;

    void setEdgeID(unsigned int edgeID);

    const std::set<Node *, NodeComp> &getTail() const;

    void setTail(const std::set<Node *, NodeComp> &tail);

    const std::set<Node *, NodeComp> &getHead() const;

    void setHead(const std::set<Node *, NodeComp> &head);

    const std::set<Node *, NodeComp> &getNodes() const;

    void setNodes(const std::set<Node *, NodeComp> &nodes);

    bool isDirected();
};

struct EdgeComp {
    bool operator()(const Edge *lhs, const Edge *rhs) const;
};

BOOST_SERIALIZATION_ASSUME_ABSTRACT(Edge)
BOOST_CLASS_EXPORT_KEY(Edge)

#endif //ARMY_ANT_CPP_EDGE_H