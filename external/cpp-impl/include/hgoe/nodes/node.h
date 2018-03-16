//
// Created by jldevezas on 3/6/18.
//

#ifndef ARMY_ANT_NODE_H
#define ARMY_ANT_NODE_H

#include <string>
#include <ostream>

#include <boost/unordered_set.hpp>
#include <boost/archive/binary_oarchive.hpp>
#include <boost/archive/binary_iarchive.hpp>
#include <boost/serialization/string.hpp>
#include <boost/serialization/export.hpp>
#include <boost/functional/hash.hpp>

class Node {
private:
    friend class boost::serialization::access;

    template<class Archive>
    void serialize(Archive &ar, unsigned int version) {
        ar & nodeID;
        ar & name;
    };
protected:
    static unsigned int nextNodeID;

    unsigned int nodeID;
    std::string name;
public:
    enum NodeLabel {
        DEFAULT = 0,
        DOCUMENT = 1,
        TERM = 2,
        ENTITY = 3
    };

    Node();

    explicit Node(std::string name);

    bool operator==(const Node &rhs) const;

    bool operator!=(const Node &rhs) const;

    friend std::ostream &operator<<(std::ostream &os, const Node &node);

    const std::string &getName() const;

    void setName(const std::string &name);

    unsigned int getNodeID() const;

    void setNodeID(unsigned int nodeID);

    virtual NodeLabel label() const = 0;
};

std::size_t hash_value(const Node &node);

BOOST_SERIALIZATION_ASSUME_ABSTRACT(Node)
BOOST_CLASS_EXPORT_KEY(Node)

#endif //ARMY_ANT_NODE_H
