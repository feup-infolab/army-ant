//
// Created by jldevezas on 3/15/18.
//

#ifndef ARMY_ANT_CPP_EDGE_SET_H
#define ARMY_ANT_CPP_EDGE_SET_H

#include <boost/serialization/shared_ptr.hpp>
#include <boost/serialization/boost_unordered_set.hpp>
#include <boost/serialization/base_object.hpp>
#include <boost/serialization/export.hpp>

#include <hgoe/edges/edge.h>

struct EdgeEqual {
    bool operator()(const boost::shared_ptr<Edge> &lhs, const boost::shared_ptr<Edge> &rhs) const;
};

struct EdgeHash {
    std::size_t operator()(const boost::shared_ptr<Edge> &edge) const;
};

typedef boost::unordered_set<boost::shared_ptr<Edge>, EdgeHash, EdgeEqual, std::allocator<boost::shared_ptr<Edge>>> EdgeSetContainer;

class EdgeSet : public EdgeSetContainer {
private:
    friend class boost::serialization::access;

    template<class Archive>
    void serialize(Archive &ar, unsigned int version) {
        ar & boost::serialization::base_object<EdgeSetContainer>(*this);
    };
public:
    using EdgeSetContainer::EdgeSetContainer;

    bool operator==(const EdgeSet &rhs) const;

    bool operator!=(const EdgeSet &rhs) const;
};

/*std::size_t hash_value(const Edge &edge);

std::size_t hash_value(const EdgeSet &edgeSet);*/

BOOST_CLASS_EXPORT_KEY(EdgeSet)

#endif //ARMY_ANT_CPP_EDGE_SET_H
