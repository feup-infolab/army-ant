//
// Created by jldevezas on 3/15/18.
//

#ifndef ARMY_ANT_CPP_NODE_SET_H
#define ARMY_ANT_CPP_NODE_SET_H

#include <ostream>

#include <boost/serialization/shared_ptr.hpp>
#include <boost/serialization/boost_unordered_set.hpp>
#include <boost/serialization/base_object.hpp>
#include <boost/serialization/export.hpp>

#include <hgoe/nodes/node.h>

struct NodeEqual {
    bool operator()(const boost::shared_ptr<Node> &lhs, const boost::shared_ptr<Node> &rhs) const;
};

struct NodeHash {
    std::size_t operator()(const boost::shared_ptr<Node> &node) const;
};

typedef boost::unordered_set<boost::shared_ptr<Node>, NodeHash, NodeEqual, std::allocator<Node>> NodeSetContainer;

class NodeSet : public NodeSetContainer {
private:
    friend class boost::serialization::access;

    template<class Archive>
    void serialize(Archive &ar, unsigned int version) {
        ar & boost::serialization::base_object<NodeSetContainer>(*this);
    };
public:
    using NodeSetContainer::NodeSetContainer;

    bool operator==(const NodeSet &rhs) const;

    bool operator!=(const NodeSet &rhs) const;

    friend std::ostream &operator<<(std::ostream &os, const NodeSet &nodeSet);
};

std::size_t hash_value(const NodeSet &nodeSet);

BOOST_CLASS_EXPORT_KEY(NodeSet)

#endif //ARMY_ANT_CPP_NODE_SET_H
