set(BOOST_ROOT /usr/local)

find_package(PythonLibs 3.6)
find_package(Boost COMPONENTS python)

include_directories(${Boost_INCLUDE_DIRS} ${PYTHON_INCLUDE_DIRS})
link_directories(${Boost_LIBRARY_DIR})

add_executable(test_armyant test_armyant.cpp)
target_link_libraries(test_armyant armyant ${Boost_LIBRARIES} ${PYTHON_LIBRARIES})
add_test(hello_test test_armyant)