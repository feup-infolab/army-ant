#include "hypergraph_of_entity.h"

#include <boost/python.hpp>

namespace {
    BOOST_PYTHON_MODULE (armyant) {
        using namespace boost::python;

        class_<HypergraphOfEntity>("HypergraphOfEntity", init<>())
                .def("test", &HypergraphOfEntity::test);
    }
}