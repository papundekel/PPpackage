cmake_minimum_required(VERSION 3.27)

project(fakealpm)

include(GNUInstallDirs)

add_executable(fakealpm "fakealpm.cpp")
target_link_libraries(fakealpm PUBLIC "alpm")
target_compile_options(fakealpm PUBLIC "-Wall" "-Wextra" "-pedantic" "-Werror")
target_compile_features(fakealpm PUBLIC cxx_std_23)
set_target_properties(fakealpm PROPERTIES EXPORT_COMPILE_COMMANDS ON)

add_executable(fakealpm-executable "executable.cpp")
target_compile_options(fakealpm-executable PUBLIC "-Wall" "-Wextra" "-pedantic"
                                                  "-Werror")
target_compile_features(fakealpm-executable PUBLIC cxx_std_23)
set_target_properties(fakealpm-executable PROPERTIES EXPORT_COMPILE_COMMANDS ON)

install(TARGETS fakealpm DESTINATION ${CMAKE_INSTALL_BINDIR})
install(TARGETS fakealpm-executable DESTINATION ${CMAKE_INSTALL_BINDIR})
