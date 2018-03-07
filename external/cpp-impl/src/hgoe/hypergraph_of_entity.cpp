//
// Created by jldevezas on 3/6/18.
//

#include <hgoe/hypergraph_of_entity.h>
#include <hgoe/nodes/node.h>
#include <hgoe/hypergraph.h>
#include <boost/python/extract.hpp>
#include <boost/tokenizer.hpp>
#include <boost/algorithm/string.hpp>

namespace py = boost::python;

HypergraphOfEntity::HypergraphOfEntity() {
    /*Node nodes[] = {
            Node("josé"),
            Node("maria"),
            Node("manuel"),
            Node("joaquim"),
            Node("josé")
    };

    Hypergraph hg = Hypergraph();

    for (auto nodes : nodes) {
        hg.getOrCreateNode(nodes);
    }

    for (auto const &nodes : hg.getNodes()) {
        std::cout << nodes.getName() << std::endl;
    }*/
}

void HypergraphOfEntity::pyIndex(boost::python::object document) {
    std::string text = py::extract<std::string>(document.attr("text"));

    boost::algorithm::to_lower(text);
    boost::tokenizer<> tok(text);
    for (auto term : tok) {
        std::cout << term << std::endl;
    }
}