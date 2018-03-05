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

find_package(PythonLibs REQUIRED)
find_package(Boost COMPONENTS python3)

include_directories(${Boost_INCLUDE_DIRS} ${PYTHON_INCLUDE_DIRS})

add_library(armyant armyant.cpp ../include/armyant.h)

target_link_libraries(armyant ${Boost_LIBRARIES} ${PYTHON_LIBRARIES})