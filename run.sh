#!/usr/bin/env sh

if [ -z "$2" ]; then
    echo "Usage: $0 [native|docker] <tmp_path> < <input>"
    exit 1
fi

mode="$1"
tmp="$2"
debug="$3"

wd="$(pwd)"
tmp_path="$wd/$tmp"
cache_path="$tmp_path/cache"
generators_path="$tmp_path/generators"
runc_path="$tmp_path/PPpackage-runc"


mkdir -p "$cache_path" "$generators_path" "$runc_path/run" "$runc_path/containers" && \
\
machine_id="$(./"run-$mode-machine-id.sh")" && \
machine_id_length="$(printf "$machine_id" | wc --bytes)" && \
\
runc_id="$(./"run-$mode-runc.sh" "$runc_path" "$debug")" && \
\
sleep 1 && \
\
container_relative_path="$(printf "$machine_id_length\n${machine_id}INIT\nEND\n" | netcat -U -q 0 "$tmp/PPpackage-runc/run/PPpackage-runc.sock" | tail --lines 1)" && \
\
./"run-$mode-PPpackage.sh" "$cache_path" "$generators_path" "$runc_path" "$container_relative_path" "$debug" && \
\
./"run-$mode-stop.sh" "$runc_id"
