#!/usr/bin/env sh

BUILD_DIR="fakealpm/build"

cmake -G "Ninja Multi-Config" -S fakealpm/ -B "$BUILD_DIR" && \
cmake --build "$BUILD_DIR" --config Release && \
cmake --install "$BUILD_DIR" --config Release --prefix "$BUILD_DIR/install"
