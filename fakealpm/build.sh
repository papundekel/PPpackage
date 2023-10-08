#!/usr/bin/env sh

mkdir -p build && \
\
g++ -Wall -shared -fPIC -o build/fakealpm.so -I /usr/share/libalpm-pp/usr/include/ fakealpm.cpp
