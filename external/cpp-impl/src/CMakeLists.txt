find_package(PythonLibs)
find_package(Boost COMPONENTS python3)

include_directories(${Boost_INCLUDE_DIRS} ${PYTHON_INCLUDE_DIRS})
link_directories(${Boost_LIBRARY_DIR})

set(SRC
    army_ant_cpp.cpp
    hypergraph.cpp
    hypergraph_of_entity.cpp
    node/node.cpp)

set(INCLUDE
    ../include/hypergraph.h
    ../include/hypergraph_of_entity.h
    ../include/node/node.h)

add_library(army_ant_cpp SHARED ${SRC} ${INCLUDE})
target_link_libraries(army_ant_cpp ${Boost_LIBRARIES} ${PYTHON_LIBRARIES})

set_target_properties(army_ant_cpp PROPERTIES SUFFIX .so)
set_target_properties(army_ant_cpp PROPERTIES PREFIX "")