#!/usr/bin/env sh

rm -rf tmp/root
./build_fakealpm.sh
./manager.sh tmp/ < tmp/input/input-basic.json
