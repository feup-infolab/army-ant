//
// Created by jldevezas on 3/8/18.
//

#ifndef ARMY_ANT_CPP_RELATED_TO_EDGE_H
#define ARMY_ANT_CPP_RELATED_TO_EDGE_H

#include <set>
#include <hgoe/edges/edge.h>
#include <hgoe/nodes/node.h>
#include <boost/serialization/base_object.hpp>
#include <boost/serialization/export.hpp>

class RelatedToEdge : public Edge {
private:
    friend class boost::serialization::access;

    template<class Archive>
    void serialize(Archive &ar, unsigned int version) {
        ar & boost::serialization::base_object<Edge>(*this);
    };
public:
    RelatedToEdge();

    explicit RelatedToEdge(std::set<Node *, NodeComp> nodes);
};

BOOST_CLASS_EXPORT_KEY(RelatedToEdge)

#endif //ARMY_ANT_CPP_RELATED_TO_EDGE_H
