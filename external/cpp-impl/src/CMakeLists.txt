ExternalProject_Add(hattrie
    GIT_REPOSITORY https://github.com/Tessil/hat-trie.git
    GIT_TAG v0.3.0
    SOURCE_DIR "${CMAKE_BINARY_DIR}/hat-trie-src"
    BINARY_DIR ""
    CONFIGURE_COMMAND ""
    BUILD_COMMAND ""
    INSTALL_COMMAND ""
    TEST_COMMAND "")

set(hattrie_INCLUDE_DIRS ${CMAKE_BINARY_DIR}/hat-trie-src)

find_package(PythonLibs)
find_package(Boost COMPONENTS python3 log serialization filesystem)

find_package(OpenMP)
set(CMAKE_C_FLAGS "${CMAKE_C_FLAGS} ${OpenMP_C_FLAGS}")
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} ${OpenMP_CXX_FLAGS}")
set(CMAKE_EXE_LINKER_FLAGS "${CMAKE_EXE_LINKER_FLAGS} ${OpenMP_EXE_LINKER_FLAGS}")

add_definitions(-DBOOST_LOG_DYN_LINK)

include_directories(${Boost_INCLUDE_DIRS} ${PYTHON_INCLUDE_DIRS} ${hattrie_INCLUDE_DIRS})
link_directories(${Boost_LIBRARY_DIR})

set(SRC
    army_ant_cpp.cpp
    engine.cpp
    structures/document.cpp
    structures/entity.cpp
    structures/result.cpp
    structures/result_set.cpp
    hgoe/hypergraph.cpp
    hgoe/hypergraph_of_entity.cpp
    hgoe/nodes/node.cpp
    hgoe/nodes/document_node.cpp
    hgoe/nodes/term_node.cpp
    hgoe/nodes/entity_node.cpp
    hgoe/nodes/node_set.cpp
    hgoe/edges/edge.cpp
    hgoe/edges/document_edge.cpp
    hgoe/edges/related_to_edge.cpp
    hgoe/edges/contained_in_edge.cpp
    hgoe/edges/edge_set.cpp)

set(INCLUDE
    ../include/engine.h
    ../include/structures/document.h
    ../include/structures/entity.h
    ../include/structures/result.h
    ../include/structures/result_set.h
    ../include/hgoe/hypergraph.h
    ../include/hgoe/hypergraph_of_entity.h
    ../include/hgoe/nodes/node.h
    ../include/hgoe/nodes/document_node.h
    ../include/hgoe/nodes/term_node.h
    ../include/hgoe/nodes/entity_node.h
    ../include/hgoe/nodes/node_set.h
    ../include/hgoe/edges/edge.h
    ../include/hgoe/edges/contained_in_edge.h
    ../include/hgoe/edges/related_to_edge.h
    ../include/hgoe/edges/document_edge.h
    ../include/hgoe/edges/edge_set.h)

add_library(army_ant_cpp SHARED ${SRC} ${INCLUDE})
target_link_libraries(army_ant_cpp ${Boost_LIBRARIES} ${PYTHON_LIBRARIES})

set_target_properties(army_ant_cpp PROPERTIES SUFFIX .so)
set_target_properties(army_ant_cpp PROPERTIES PREFIX "")