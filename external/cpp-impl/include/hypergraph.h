//
// Created by jldevezas on 3/6/18.
//

#ifndef ARMYANT_HYPERGRAPH_H
#define ARMYANT_HYPERGRAPH_H

#include <string>
#include <set>
#include <node/node.h>
#include <boost/python/object.hpp>

class Hypergraph {
private:
    std::set<Node> nodes;
public:
    void index(boost::python::object document);
    Node getOrCreateNode(Node node);

    const std::set<Node> &getNodes() const;
};

#endif //ARMYANT_HYPERGRAPH_H
