#include "hgoe/hypergraph_of_entity.h"

#include <boost/python.hpp>

namespace {
    BOOST_PYTHON_MODULE (army_ant_cpp) {
        using namespace boost::python;

        class_<HypergraphOfEntity>("HypergraphOfEntity", init<std::string>())
                .def("index", &HypergraphOfEntity::pyIndex)
                .def("post_processing", &HypergraphOfEntity::postProcessing)
                .def("save", &HypergraphOfEntity::save)
                .def("load", &HypergraphOfEntity::load);
    }
}