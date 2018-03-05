#include "armyant.h"

#include <iostream>

#include <boost/python.hpp>

BOOST_PYTHON_MODULE (armyant) {
    using namespace boost::python;
    class_<HypergraphOfEntity>("HypergraphOfEntity", init<>())
            .def("hello", &HypergraphOfEntity::hello);
}

void HypergraphOfEntity::hello() {
    std::cout << "Hello, World!" << std::endl;
}