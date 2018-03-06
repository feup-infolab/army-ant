#ExternalProject_Add(Hypergraph
#  GIT_REPOSITORY    https://github.com/alex-87/HyperGraphLib.git
#  GIT_TAG           HyperGraphLib-v2.0
#  SOURCE_DIR        "${CMAKE_BINARY_DIR}/hypergraph-src"
#  BINARY_DIR        "${CMAKE_BINARY_DIR}/hypergraph-build"
#  CONFIGURE_COMMAND ""
#  BUILD_COMMAND     ""
#  INSTALL_COMMAND   ""
#  TEST_COMMAND      ""
#)

find_package(PythonLibs)
find_package(Boost COMPONENTS python3)

#ExternalProject_Get_Property(Hypergraph source_dir)
#include_directories(${source_dir}/include)

include_directories(${Boost_INCLUDE_DIRS} ${PYTHON_INCLUDE_DIRS})
link_directories(${Boost_LIBRARY_DIR})

add_library(armyant SHARED armyant.cpp hypergraph_of_entity.cpp ../include/hypergraph_of_entity.h)
#add_dependencies(armyant Hypergraph)

target_link_libraries(armyant ${Boost_LIBRARIES} ${PYTHON_LIBRARIES} hypergraph)

set_target_properties(armyant PROPERTIES SUFFIX .so)
set_target_properties(armyant PROPERTIES PREFIX "")