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

include_directories(${Boost_INCLUDE_DIRS} ${PYTHON_INCLUDE_DIRS} ${hattrie_INCLUDE_DIRS})
link_directories(${Boost_LIBRARY_DIR})

set(SRC
    army_ant_cpp.cpp
    engine.cpp
    structures/document.cpp
    structures/entity.cpp
    hgoe/hypergraph.cpp
    hgoe/hypergraph_of_entity.cpp
    hgoe/nodes/node.cpp
    hgoe/nodes/document_node.cpp
    hgoe/nodes/term_node.cpp
    hgoe/nodes/entity_node.cpp
    hgoe/edges/edge.cpp
    hgoe/edges/document_edge.cpp
    hgoe/edges/related_to_edge.cpp
    hgoe/edges/contained_in_edge.cpp)

set(INCLUDE
    ../include/engine.h
    ../include/structures/document.h
    ../include/structures/entity.h
    ../include/hgoe/hypergraph.h
    ../include/hgoe/hypergraph_of_entity.h
    ../include/hgoe/nodes/node.h
    ../include/hgoe/nodes/document_node.h
    ../include/hgoe/nodes/term_node.h
    ../include/hgoe/nodes/entity_node.h
    ../include/hgoe/edges/edge.h
    ../include/hgoe/edges/contained_in_edge.h
    ../include/hgoe/edges/related_to_edge.h
    ../include/hgoe/edges/document_edge.h)

add_library(army_ant_cpp SHARED ${SRC} ${INCLUDE})
target_link_libraries(army_ant_cpp ${Boost_LIBRARIES} ${PYTHON_LIBRARIES})

set_target_properties(army_ant_cpp PROPERTIES SUFFIX .so)
set_target_properties(army_ant_cpp PROPERTIES PREFIX "")