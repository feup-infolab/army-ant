cmake_minimum_required(VERSION 3.9)

project(armyant)

set(CMAKE_CXX_STANDARD 17)

set(CMAKE_MODULE_PATH "${CMAKE_SOURCE_DIR}")

include(CTest)
enable_testing()

include(CheckIncludeFile)
include(CheckIncludeFileCXX)
include(CheckIncludeFiles)
include(ExternalProject)

include_directories(${CMAKE_CURRENT_SOURCE_DIR}/include)

add_subdirectory(src)
add_subdirectory(test)