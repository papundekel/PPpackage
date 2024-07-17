#!/bin/bash

cmake -S /mnt/source -B /mnt/build -DCMAKE_TOOLCHAIN_FILE=/mnt/generators/conan_toolchain.cmake -DCMAKE_BUILD_TYPE=Release
cmake --build /mnt/build
