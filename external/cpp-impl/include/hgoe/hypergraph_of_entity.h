//
// Created by jldevezas on 3/6/18.
//

#ifndef ARMYANT_HYPERGRAPH_OF_ENTITY_H
#define ARMYANT_HYPERGRAPH_OF_ENTITY_H

#include <chrono>
#include <iostream>
#include <set>

#include <boost/python/object.hpp>
#include <boost/filesystem.hpp>

#include <engine.h>
#include <structures/document.h>
#include <hgoe/nodes/node.h>
#include <hgoe/hypergraph.h>

namespace py = boost::python;

class HypergraphOfEntity : Engine {
private:
    boost::filesystem::path baseDirPath;
    boost::filesystem::path hgFilePath;
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

    NodeSet indexEntities(Document document);

    void postProcessing();

    void linkTextAndKnowledge();

    void save();

    void load();
};

#endif //ARMYANT_HYPERGRAPH_OF_ENTITY_H
