#!/usr/bin/env sh

if [ -z "$1" ]; then
    echo "Usage: $0 <tmp_path>"
    exit 1
fi

mkdir -p "$1/cache" "$1/generators" "$1/PPpackage-runc" && \
\
machine_id=$(docker run --rm fackop/pppackage head --lines=1 /etc/machine-id) && \
\
./PPpackage_runc.py "$1/PPpackage-runc" && sleep 1 && \
\
container_path=$(printf "32\n${machine_id}INIT\nEND\n" | netcat -U -q 0 $1/PPpackage-runc/PPpackage-runc.sock | tail --lines 1) && \
\
docker run \
    --interactive \
    --rm \
    --ulimit "nofile=1024:1048576" \
    --mount type=bind,readonly,source="/etc/passwd",destination="/etc/passwd" \
    --mount type=bind,readonly,source="/etc/group",destination="/etc/group" \
    --user "$(id -u):$(id -g)" \
    --mount type=bind,source="$(pwd)/$1/cache",destination="/workdir/tmp/cache" \
    --mount type=bind,source="$(pwd)/$1/generators",destination="/workdir/tmp/generators" \
    --mount type=bind,source="$(pwd)/$1/PPpackage-runc/PPpackage-runc.sock",destination="/run/PPpackage-runc.sock" \
    --mount type=bind,source="$(pwd)/$1/PPpackage-runc/containers/$machine_id",destination="/mnt/PPpackage-runc/" \
    fackop/pppackage ./manager.sh tmp/ /run/PPpackage-runc.sock /mnt/PPpackage-runc/ root/ && \
\
kill -s TERM $(cat "$1/PPpackage-runc/PPpackage-runc.pid")
