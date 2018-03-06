find_package(PythonLibs)

include_directories(${PYTHON_INCLUDE_DIRS})

add_executable(test_armyant test_armyant.cpp)
target_link_libraries(test_armyant army_ant_cpp ${PYTHON_LIBRARIES})
add_test(test_test test_armyant)