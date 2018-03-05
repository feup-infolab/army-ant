add_executable(armyant_test test_armyant.cpp)
target_link_libraries (armyant_test armyant)
add_test(hello_test armyant_test)