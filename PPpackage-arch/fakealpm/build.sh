#!/usr/bin/env sh

SOURCE_DIR="PPpackage-arch/fakealpm"
BUILD_DIR="$SOURCE_DIR/build"

cmake -G "Ninja Multi-Config" -S "$SOURCE_DIR" -B "$BUILD_DIR" && \
cmake --build "$BUILD_DIR" --config Release && \
cmake --install "$BUILD_DIR" --config Release --prefix "$BUILD_DIR/install"
