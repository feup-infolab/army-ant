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
    std::string path;
    Hypergraph hg;
    std::chrono::milliseconds totalTime;
    float avgTimePerDocument;
    unsigned int counter;
public:
    HypergraphOfEntity();

    explicit HypergraphOfEntity(std::string path);

    void pyIndex(py::object document);

    void index(Document document);

    void indexDocument(Document document);

    std::set<Node> indexEntities(Document document);

    void postProcessing();

    void linkTextAndKnowledge();
};

#endif //ARMYANT_HYPERGRAPH_OF_ENTITY_H
