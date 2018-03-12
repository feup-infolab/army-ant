//
// Created by jldevezas on 3/8/18.
//

#ifndef ARMY_ANT_CPP_CONTAINED_IN_EDGE_H
#define ARMY_ANT_CPP_CONTAINED_IN_EDGE_H

#include "edge.h"
#include <boost/serialization/base_object.hpp>
#include <boost/serialization/export.hpp>

class ContainedInEdge : public Edge {
private:
    friend class boost::serialization::access;

    template<class Archive>
    void serialize(Archive &ar, unsigned int version) {
        ar & boost::serialization::base_object<Edge>(*this);
    };
public:
    ContainedInEdge();

    explicit ContainedInEdge(std::set<Node *, NodeComp> tail, std::set<Node *, NodeComp> head);
};

BOOST_CLASS_EXPORT_KEY(ContainedInEdge)

#endif //ARMY_ANT_CPP_CONTAINED_IN_EDGE_H
