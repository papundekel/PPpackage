#!/usr/bin/env sh

rm -rf tmp/root
./build_fakealpm.sh
./manager.sh tmp/ < tmp/input/input-basic.json
cp -r tmp/aborting-hook/usr/ tmp/root/
./manager.sh tmp/ < tmp/input/input-ninja.json
