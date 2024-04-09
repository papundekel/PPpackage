cmake_minimum_required(VERSION 3.27)

project(fakealpm)

include(GNUInstallDirs)

add_library(fakealpm SHARED "fakealpm.cpp")
target_compile_options(fakealpm PUBLIC "-Wall" "-Wextra" "-pedantic" "-Werror")
target_compile_features(fakealpm PUBLIC cxx_std_23)
set_target_properties(fakealpm PROPERTIES EXPORT_COMPILE_COMMANDS ON)
target_include_directories(fakealpm PUBLIC "/usr/share/libalpm-pp/usr/include/")

install(TARGETS fakealpm DESTINATION ${CMAKE_INSTALL_LIBDIR})
