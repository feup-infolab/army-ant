ExternalProject_Add(hypergraph
  GIT_REPOSITORY    https://github.com/alex-87/HyperGraphLib.git
  GIT_TAG           HyperGraphLib-v2.0
  SOURCE_DIR        "${CMAKE_BINARY_DIR}/hypergraph-src"
  BINARY_DIR        "${CMAKE_BINARY_DIR}/hypergraph-build"
  CONFIGURE_COMMAND ""
  BUILD_COMMAND     ""
  INSTALL_COMMAND   ""
  TEST_COMMAND      ""
)

set(BOOST_ROOT /usr/local)

find_package(PythonLibs 3.6)
find_package(Boost COMPONENTS python3)

include_directories(${Boost_INCLUDE_DIRS} ${PYTHON_INCLUDE_DIRS})
link_directories(${Boost_LIBRARY_DIR})

add_library(armyant SHARED armyant.cpp ../include/armyant.h)
target_link_libraries(armyant ${Boost_LIBRARIES} ${PYTHON_LIBRARIES})

set_target_properties(armyant PROPERTIES SUFFIX .so)
set_target_properties(armyant PROPERTIES PREFIX "")