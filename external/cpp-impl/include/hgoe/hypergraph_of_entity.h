//
// Created by jldevezas on 3/6/18.
//

#ifndef ARMYANT_HYPERGRAPH_OF_ENTITY_H
#define ARMYANT_HYPERGRAPH_OF_ENTITY_H

#include <chrono>
#include <Hypergraph/model/Hypergraphe.hh>
#include <iostream>
#include <boost/python/object.hpp>
#include <engine.h>
#include <structures/document.h>
#include <hgoe/nodes/node.h>
#include <set>
#include "hypergraph.h"

namespace py = boost::python;

class HypergraphOfEntity : Engine {
private:
    Hypergraph hg;
    std::chrono::duration<long, std::ratio<1, 10000000000>> totalTime;
    std::chrono::duration<long, std::ratio<1, 10000000000>> avgTimePerDocument;
    unsigned int counter;
public:
    HypergraphOfEntity();

    void pyIndex(py::object document);

    void index(Document document);

    void indexDocument(Document document);

    std::set<Node> indexEntities(Document document);

    void linkTextAndKnowledge();
};

#endif //ARMYANT_HYPERGRAPH_OF_ENTITY_H
