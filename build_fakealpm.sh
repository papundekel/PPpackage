#!/usr/bin/env sh

g++ -Wall -shared -fPIC -o fakealpm/build/fakealpm.so -I /usr/share/libalpm-pp/usr/include/ fakealpm/fakealpm.cpp
