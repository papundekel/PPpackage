#!/usr/bin/env sh

if [ "$#" -ne 0 ]; then
    echo "Usage: $0 <input.json"
    exit 1
fi

mkdir -p tmp/output
mkdir -p tmp/cache/product

python \
    -m PPpackage.metamanager \
    tmp/root/ \
    --config examples/native/all-local/config.json \
    --generators tmp/output/generators \
    --graph tmp/output/graph.dot
