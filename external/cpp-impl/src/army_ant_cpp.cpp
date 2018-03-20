#include <boost/python.hpp>

#include <hgoe/hypergraph_of_entity.h>
#include <hgoe/nodes/entity_node.h>

namespace {
    BOOST_PYTHON_MODULE (army_ant_cpp) {
        using namespace boost::python;
        using self_ns::str;

        class_<HypergraphOfEntity>("HypergraphOfEntity", init<std::string>())
                .def("index", &HypergraphOfEntity::pyIndex)
                .def("search", &HypergraphOfEntity::pySearch)
                .def("post_processing", &HypergraphOfEntity::postProcessing)
                .def("save", &HypergraphOfEntity::save)
                .def("load", &HypergraphOfEntity::load);

        class_<Result>("Result")
                .def("get_score", &Result::getScore)
                .def("get_doc_id", &Result::getDocID, return_value_policy<copy_const_reference>())
                .def(str(self));

        class_<ResultSet>("ResultSet")
                .def("__iter__", iterator<ResultSet>());
    }
}