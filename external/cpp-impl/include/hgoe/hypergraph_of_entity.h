//
// Created by jldevezas on 3/6/18.
//

#ifndef ARMYANT_HYPERGRAPH_OF_ENTITY_H
#define ARMYANT_HYPERGRAPH_OF_ENTITY_H

#include <Hypergraph/model/Hypergraphe.hh>
#include <iostream>
#include <boost/python/object.hpp>
#include <engine.h>
#include <structures/document.h>

namespace py = boost::python;

class HypergraphOfEntity : Engine {
private:
    std::string str;
public:
    HypergraphOfEntity();

    void pyIndex(py::object document);

    void index(Document document);
};

#endif //ARMYANT_HYPERGRAPH_OF_ENTITY_H
