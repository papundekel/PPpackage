#!/usr/bin/env sh

if [ -z "$1" ]; then
    echo "Usage: $0 <tmp_path>"
    exit 1
fi

mkdir -p "$1/cache" "$1/generators" "$1/root"

docker run \
    --interactive \
    --rm \
    --ulimit "nofile=1024:1048576" \
    --mount type=bind,readonly,source="/etc/passwd",destination="/etc/passwd" \
    --mount type=bind,readonly,source="/etc/group",destination="/etc/group" \
    --user "$(id -u):$(id -g)" \
    --mount type=bind,source="$(pwd)/$1/cache,destination"="/workdir/tmp/cache" \
    --mount type=bind,source="$(pwd)/$1/generators,destination"="/workdir/tmp/generators" \
    --mount type=bind,source="$(pwd)/$1/root,destination"="/workdir/tmp/root" \
    fackop/pppackage ./manager.sh tmp/
