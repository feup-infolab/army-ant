find_package(PythonLibs)

include_directories(${PYTHON_INCLUDE_DIRS})

set(TESTS
    node
    edge
    hypergraph
    hypergraph_of_entity)

foreach (test ${TESTS})
  add_executable(test_${test} test_${test}.cpp)
  target_link_libraries(test_${test} army_ant_cpp ${PYTHON_LIBRARIES})
  add_test(test_${test} test_${test})
endforeach ()