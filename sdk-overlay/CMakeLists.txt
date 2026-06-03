cmake_minimum_required(VERSION 3.0)
project(unitree_lidar_sdk)

set(CMAKE_BUILD_TYPE "Release")
set(CMAKE_CXX_FLAGS "-std=c++17")
set(CMAKE_CXX_FLAGS_DEBUG "$ENV{CXXFLAGS} -O0 -Wall -g2 -ggdb")
set(CMAKE_CXX_FLAGS_RELEASE "$ENV{CXXFLAGS} -O3 -Wall -DNDEBUG")

include_directories(include)

link_directories(lib/${CMAKE_SYSTEM_PROCESSOR})

SET(EXECUTABLE_OUTPUT_PATH ${PROJECT_SOURCE_DIR}/bin)
set(CMAKE_ARCHIVE_OUTPUT_DIRECTORY ${PROJECT_SOURCE_DIR}/lib/${CMAKE_SYSTEM_PROCESSOR})

# --- stock priklady (puvodni) ---
add_executable(example_lidar_udp    examples/example_lidar_udp.cpp)
target_link_libraries(example_lidar_udp    libunilidar_sdk2.a)

add_executable(example_lidar_serial examples/example_lidar_serial.cpp)
target_link_libraries(example_lidar_serial libunilidar_sdk2.a)

add_executable(set_ip_address       examples/set_ip_address.cpp)
target_link_libraries(set_ip_address       libunilidar_sdk2.a)

add_executable(set_to_serial_mode   examples/set_to_serial_mode.cpp)
target_link_libraries(set_to_serial_mode   libunilidar_sdk2.a)

add_executable(set_to_udp_mode      examples/set_to_udp_mode.cpp)
target_link_libraries(set_to_udp_mode      libunilidar_sdk2.a)

# --- vlastni nastroje projektu (doplneno, aby sly rebuildnout lokalne) ---
add_executable(read_udp       examples/read_udp.cpp)
target_link_libraries(read_udp       libunilidar_sdk2.a)

add_executable(read_serial    examples/read_serial.cpp)
target_link_libraries(read_serial    libunilidar_sdk2.a)

add_executable(stream_cloud   examples/stream_cloud.cpp)
target_link_libraries(stream_cloud   libunilidar_sdk2.a)

add_executable(dump_cloud     examples/dump_cloud.cpp)
target_link_libraries(dump_cloud     libunilidar_sdk2.a)

add_executable(lidar_motor    examples/lidar_motor.cpp)
target_link_libraries(lidar_motor    libunilidar_sdk2.a)

add_executable(record_seq     examples/record_seq.cpp)
target_link_libraries(record_seq     libunilidar_sdk2.a)

add_executable(record_glim    examples/record_glim.cpp)
target_link_libraries(record_glim    libunilidar_sdk2.a)

add_executable(scan_cloud     examples/scan_cloud.cpp)
target_link_libraries(scan_cloud     libunilidar_sdk2.a)
