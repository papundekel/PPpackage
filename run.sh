#!/usr/bin/env sh

if [ -z "$1" ]; then
    echo "Usage: $0 <tmp_path>"
    exit 1
fi

tmp="$1"

wd="$(pwd)"
cache_path="$wd/$tmp/cache"
generators_path="$wd/$tmp/generators"
run_path="$wd/$tmp/PPpackage-runc/run"
containers_path="$wd/$tmp/PPpackage-runc/containers"

mkdir -p "$cache_path" "$generators_path" "$run_path" "$containers_path" && \
\
machine_id=$(docker run --rm fackop/pppackage head --lines=1 /etc/machine-id) && \
machine_id_length=$(printf "$machine_id" | wc --bytes) && \
\
docker run \
    --privileged \
    --init \
    --detach \
    --user "$(id -u):$(id -g)" \
    --name fackop-pppackage-runc \
    --mount type=bind,source="$run_path",destination="/workdir/PPpackage-runc/run" \
    --mount type=bind,source="$containers_path",destination="/workdir/PPpackage-runc/containers" \
    fackop/pppackage-runc PPpackage-runc PPpackage-runc/ && \
\
sleep 1 && \
\
container_path="$containers_path/$(printf "$machine_id_length\n${machine_id}INIT\nEND\n" | netcat -U -q 0 $tmp/PPpackage-runc/run/PPpackage-runc.sock | tail --lines 1)" && \
\
docker run \
    --rm \
    --interactive \
    --ulimit "nofile=1024:1048576" \
    --mount type=bind,readonly,source="/etc/passwd",destination="/etc/passwd" \
    --mount type=bind,readonly,source="/etc/group",destination="/etc/group" \
    --user "$(id -u):$(id -g)" \
    --mount type=bind,source="$cache_path",destination="/workdir/tmp/cache" \
    --mount type=bind,source="$generators_path",destination="/workdir/tmp/generators" \
    --mount type=bind,source="$run_path/PPpackage-runc.sock",destination="/run/PPpackage-runc.sock" \
    --mount type=bind,source="$container_path",destination="/mnt/PPpackage-runc/" \
    fackop/pppackage PPpackage tmp/cache tmp/generators /run/PPpackage-runc.sock /mnt/PPpackage-runc/ root/ && \
\
docker stop fackop-pppackage-runc && \
docker logs fackop-pppackage-runc && \
docker container rm fackop-pppackage-runc
