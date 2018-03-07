//
// Created by jldevezas on 3/6/18.
//

#ifndef ARMYANT_NODE_H
#define ARMYANT_NODE_H

#include <string>

class Node {
private:
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
};

#endif //ARMYANT_NODE_H
