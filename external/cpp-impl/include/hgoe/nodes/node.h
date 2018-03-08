//
// Created by jldevezas on 3/6/18.
//

#ifndef ARMYANT_NODE_H
#define ARMYANT_NODE_H

#include <string>
#include <boost/archive/binary_oarchive.hpp>
#include <boost/archive/binary_iarchive.hpp>

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
        ar & name;
    };

    std::string name;
public:
    Node();

    explicit Node(std::string name);

    const std::string &getName() const;

    void setName(const std::string &name);

    bool operator<(const Node &rhs) const;

    bool operator>(const Node &rhs) const;

    bool operator<=(const Node &rhs) const;

    bool operator>=(const Node &rhs) const;

    virtual NodeLabel label();
};

#endif //ARMYANT_NODE_H
