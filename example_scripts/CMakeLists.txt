cmake_minimum_required(VERSION 3.10)

# Set the project name
project(RandomChunkPublisher)

# Set the C++ standard
set(CMAKE_CXX_STANDARD 11)
set(CMAKE_CXX_STANDARD_REQUIRED True)

# Add the executable
add_executable(RandomChunkPublisher publisher.cpp)

# Find the ZeroMQ package
find_package(PkgConfig REQUIRED)
pkg_check_modules(PC_ZMQ REQUIRED libzmq)

# Include ZeroMQ directories
include_directories(${PC_ZMQ_INCLUDE_DIRS})

# Link ZeroMQ libraries
target_link_libraries(RandomChunkPublisher ${PC_ZMQ_LIBRARIES})
