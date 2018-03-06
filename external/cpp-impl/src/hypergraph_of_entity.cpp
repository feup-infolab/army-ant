//
// Created by jldevezas on 3/6/18.
//

#include <hypergraph_of_entity.h>
#include <node/node.h>
#include <hypergraph.h>
#include <boost/python/extract.hpp>
#include <boost/tokenizer.hpp>
#include <boost/algorithm/string.hpp>

HypergraphOfEntity::HypergraphOfEntity() {
    /*Node nodes[] = {
            Node("josé"),
            Node("maria"),
            Node("manuel"),
            Node("joaquim"),
            Node("josé")
    };

    Hypergraph hg = Hypergraph();

    for (auto node : nodes) {
        hg.getOrCreateNode(node);
    }

    for (auto const &node : hg.getNodes()) {
        std::cout << node.getName() << std::endl;
    }*/
}

void HypergraphOfEntity::index(boost::python::object document) {
    std::string text = boost::python::extract<std::string>(document.attr("text"));

    boost::algorithm::to_lower(text);
    boost::tokenizer<> tok(text);
    for (auto term : tok) {
        std::cout << term << std::endl;
    }
}