# SPDX-License-Identifier: GPL-3.0-only
cmake_minimum_required(VERSION 3.25)
project(elo_client VERSION 0.1.0 LANGUAGES CXX)
set(ELO_CXX_STANDARD 23 CACHE STRING "Client standard: portable 23 or experimental 26")
if(NOT ELO_CXX_STANDARD MATCHES "^(23|26)$")
  message(FATAL_ERROR "ELO_CXX_STANDARD must be 26 or 23")
endif()
set(CMAKE_CXX_STANDARD "${ELO_CXX_STANDARD}")
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
include(CheckCXXSourceCompiles)
check_cxx_source_compiles("
  #include <string>
  #include <string_view>
  #include <variant>
  #include <vector>
  #include <map>
  #include <cstdint>
  int main() {
    std::variant<std::string, std::string_view> event{std::string{\"fixture\"}};
    std::vector<std::string> pages{\"local\"};
    std::map<std::string, std::uint64_t> pending;
    pending.emplace(pages.front(), 1);
    return std::visit([](const auto& value) { return value.empty(); }, event) || pending.empty();
  }" ELO_CORE_CXX${ELO_CXX_STANDARD}_LOCAL_CONTRACTS_COMPILES)
if(NOT ELO_CORE_CXX${ELO_CXX_STANDARD}_LOCAL_CONTRACTS_COMPILES)
  message(FATAL_ERROR "Compiler/library cannot build the core's required standard library features")
endif()
option(ELO_BUILD_GUI "Build the Qt Quick frontend" ON)
option(ELO_BUILD_TESTS "Build client contract tests" OFF)
add_library(elo-core STATIC core/client.cpp)
target_include_directories(elo-core PUBLIC "${CMAKE_CURRENT_SOURCE_DIR}")
add_executable(elo-client-core core/main.cpp)
target_link_libraries(elo-client-core PRIVATE elo-core)
install(TARGETS elo-client-core RUNTIME DESTINATION bin)
if(ELO_BUILD_GUI)
  find_package(Qt6 6.4 REQUIRED COMPONENTS Core Gui Quick Qml Network)
  set(CMAKE_AUTOMOC ON)
  qt_add_executable(elo-client main.cpp ContentSync.cpp ContentSync.hpp ClientModel.cpp ClientModel.hpp QtAdapters.cpp QtAdapters.hpp)
  qt_add_resources(elo-client "elo_ui" PREFIX "/" FILES Main.qml MorfoTheme.js)
  target_link_libraries(elo-client PRIVATE elo-core Qt6::Core Qt6::Gui Qt6::Quick Qt6::Qml Qt6::Network)
  install(TARGETS elo-client RUNTIME DESTINATION bin)
endif()
if(ELO_BUILD_TESTS)
  enable_testing()
  add_executable(elo-core-test tests/core-test.cpp)
  target_link_libraries(elo-core-test PRIVATE elo-core)
  add_test(NAME elo-core-contract COMMAND elo-core-test)
  if(ELO_BUILD_GUI)
    find_package(Qt6 REQUIRED COMPONENTS Test)
    qt_add_executable(elo-ui-test tests/ui-test.cpp ClientModel.cpp ClientModel.hpp QtAdapters.cpp QtAdapters.hpp)
    qt_add_resources(elo-ui-test "elo_test_ui" PREFIX "/" FILES Main.qml MorfoTheme.js)
    target_link_libraries(elo-ui-test PRIVATE elo-core Qt6::Core Qt6::Gui Qt6::Quick Qt6::Qml Qt6::Test)
    add_test(NAME elo-ui-contract COMMAND elo-ui-test)
    set_tests_properties(elo-ui-contract PROPERTIES TIMEOUT 30)
  endif()
endif()
install(FILES COPYING DESTINATION share/licenses/elo-client)
