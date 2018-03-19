#include <boost/python.hpp>

#include <hgoe/hypergraph_of_entity.h>

namespace {
    BOOST_PYTHON_MODULE (army_ant_cpp) {
        using namespace boost::python;

        class_<HypergraphOfEntity>("HypergraphOfEntity", init<std::string>())
                .def("index", &HypergraphOfEntity::pyIndex)
                .def("search", &HypergraphOfEntity::pySearch)
                .def("post_processing", &HypergraphOfEntity::postProcessing)
                .def("save", &HypergraphOfEntity::save)
                .def("load", &HypergraphOfEntity::load);

        class_<Result>("Result")
                .def("get_score", &Result::getScore);

        class_<ResultSet>("ResultSet")
                .def("__iter__", iterator<ResultSet>());
    }
}