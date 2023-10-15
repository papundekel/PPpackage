#!/usr/bin/env sh

if [ -z "$2" ]; then
    echo "Usage: $0 [native|docker] <cache_path> <generators_path> <destination_path> [--debug] < <input>"
    exit 1
fi

mode="$1"

cache_path="$2"
generators_path="$3"
destination_path="$4"

debug="$5"

run_path="$XDG_RUNTIME_DIR"
runner_path="$run_path/PPpackage-runner.sock"

runner_workdirs_path="$(mktemp -d)" && \
\
mkdir -p "$cache_path" "$generators_path" "$destination_path" && \
\
machine_id="$(./"run-$mode-machine-id.sh")" && \
machine_id_length="$(printf "$machine_id" | wc --bytes)" && \
\
runc_id="$(./"run-$mode-runc.sh" "$run_path" "$runner_workdirs_path" "$debug")" && \
\
sleep 1 && \
\
container_workdir_path="$runner_workdirs_path/$(printf "$machine_id_length\n${machine_id}INIT\nEND\n" | netcat -U -q 0 "$runner_path" | tail --lines 1)" && \
\
./"run-$mode-PPpackage.sh" "$runner_path" "$container_workdir_path" "$cache_path" "$generators_path" "$destination_path" "$debug"

rm -rf "$runner_workdirs_path" && \
./"run-$mode-stop.sh" "$runc_id"
