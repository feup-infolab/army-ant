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
#include <boost/container/map.hpp>
#include <boost/variant.hpp>
#include <boost/random/mersenne_twister.hpp>

#include <engine.h>
#include <structures/document.h>
#include <hgoe/nodes/node.h>
#include <hgoe/hypergraph.h>

namespace py = boost::python;

typedef boost::container::map<boost::shared_ptr<Node>, double> WeightedNodeSet;
typedef boost::container::map<boost::shared_ptr<Node>, int> IntWeightedNodeSet;
typedef boost::container::map<std::string, boost::variant<int, unsigned int, float, unsigned float, std::string>> RankingParams;

class HypergraphOfEntity : Engine {
private:
    boost::filesystem::path baseDirPath;
    boost::filesystem::path hgFilePath;
    Hypergraph hg;
    std::chrono::milliseconds totalTime;
    float avgTimePerDocument;
    unsigned int counter;
protected:
    static const boost::random::mt19937 RNG;
public:
    enum RankingFunction {
        RANDOM_WALK
    };

    static const unsigned int DEFAULT_WALK_LENGTH = 2;
    static const unsigned int DEFAULT_WALK_REPEATS = 100;

    template<class TSet, class TElement>
    static boost::shared_ptr<TElement> getRandom(TSet elementSet);

    HypergraphOfEntity();

    explicit HypergraphOfEntity(std::string path);

    void pyIndex(py::object document);

    void index(Document document) override;

    void indexDocument(Document document);

    NodeSet indexEntities(Document document);

    void postProcessing() override;

    void linkTextAndKnowledge();

    NodeSet getQueryTermNodes(const std::vector<std::string> &tokens);

    NodeSet getSeedNodes(const NodeSet &queryTermNodes);

    WeightedNodeSet seedNodeConfidenceWeights(const NodeSet &seedNodes, const NodeSet &queryTermNodes);

    Path randomWalk(boost::shared_ptr<Node> startNode, unsigned int length);

    void randomStep(boost::shared_ptr<Node> node, unsigned int remainingSteps, Path &path);

    ResultSet randomWalkSearch(const NodeSet &seedNodes, const WeightedNodeSet &seedNodeWeights,
                               unsigned int walkLength, unsigned int walkRepeats);

    ResultSet search(std::string query, unsigned int offset, unsigned int limit) override;

    ResultSet search(std::string query, unsigned int offset, unsigned int limit,
                     RankingFunction function, RankingParams params);

    void save();

    void load();
};

#endif //ARMYANT_HYPERGRAPH_OF_ENTITY_H
