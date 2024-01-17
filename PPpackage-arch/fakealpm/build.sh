#!/usr/bin/env sh

cmake -G "Ninja Multi-Config" -S "$1" -B "$2" && \
cmake --build "$2" --config Release && \
cmake --install "$2" --config Release --prefix "$3"
