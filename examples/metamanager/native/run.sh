#!/usr/bin/env sh

if [ "$#" -ne 0 ]; then
    echo "Usage: $0 <input.json"
    exit 1
fi

python \
    -m PPpackage.metamanager \
    tmp/root/ \
    --config examples/metamanager/native/config.json \
    --generators tmp/output/generators \
    --graph tmp/output/graph.dot
