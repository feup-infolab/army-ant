//
// Created by jldevezas on 3/6/18.
//

#ifndef ARMYANT_HYPERGRAPH_OF_ENTITY_H
#define ARMYANT_HYPERGRAPH_OF_ENTITY_H

#include <Hypergraph/model/Hypergraphe.hh>
#include <iostream>
#include <boost/python/object.hpp>

class HypergraphOfEntity {
private:
    std::string str;
public:
    HypergraphOfEntity();

    void index(boost::python::object document);
};

#endif //ARMYANT_HYPERGRAPH_OF_ENTITY_H
