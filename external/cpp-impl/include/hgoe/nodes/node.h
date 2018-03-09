//
// Created by jldevezas on 3/6/18.
//

#ifndef ARMYANT_NODE_H
#define ARMYANT_NODE_H

#include <string>
#include <boost/archive/binary_oarchive.hpp>
#include <boost/archive/binary_iarchive.hpp>
#include <boost/serialization/string.hpp>
#include <boost/serialization/export.hpp>

enum NodeLabel {
    DEFAULT,
    TERM,
    ENTITY,
    DOCUMENT
};

class Node {
private:
    friend class boost::serialization::access;

    template<class Archive>
    void serialize(Archive &ar, unsigned int version) {
        ar & nodeID;
        ar & name;
    };

    unsigned int nodeID;
    std::string name;
protected:
    static unsigned int nextNodeID;
public:
    Node();

    explicit Node(std::string name);

    const std::string &getName() const;

    void setName(const std::string &name);

    unsigned int getNodeID() const;

    void setNodeID(unsigned int nodeID);

    virtual NodeLabel label()=0;

    bool operator<(const Node &rhs) const;

    bool operator>(const Node &rhs) const;

    bool operator<=(const Node &rhs) const;

    bool operator>=(const Node &rhs) const;
};

BOOST_SERIALIZATION_ASSUME_ABSTRACT(Node)
BOOST_CLASS_EXPORT_KEY(Node)

#endif //ARMYANT_NODE_H
