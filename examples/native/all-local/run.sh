#!/usr/bin/env sh

if [ "$#" -ne 0 ]; then
    echo "Usage: $0 <input.json"
    exit 1
fi

mkdir -p tmp/output

python \
    -m PPpackage \
    tmp/root/ \
    --config examples/native/all-local/config.json \
    --workdir /tmp \
    --generators tmp/output/generators \
    --graph tmp/output/graph.dot
