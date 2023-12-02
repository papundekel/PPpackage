#!/usr/bin/env sh

if [ -z "$2" ]; then
    echo "Usage: $0 [native|docker] <cache_path> <generators_path> <destination_path> [--update-database|--no-update-database] [--debug|--no-debug] < <input>"
    exit 1
fi

mode="$1"

cache_path="$2"
generators_path="$3"
destination_path="$4"

update_database="$5"
debug="$6"

run_path="$XDG_RUNTIME_DIR"
runner_path="$run_path/PPpackage-runner.sock"

runner_workdirs_path="$(mktemp -d)" && \
\
mkdir -p "$cache_path" "$generators_path" "$destination_path" && \
\
machine_id="$(./"run-$mode-machine-id.sh")" && \
\
runner_id="$(./"run-$mode-runner.sh" "$run_path" "$runner_workdirs_path" "$debug")" && \
\
sleep 1 && \
container_workdir_path="$runner_workdirs_path/$(./"run-$mode-init.sh" "$runner_path" "$machine_id" "$debug")" && \
\
./"run-$mode-PPpackage.sh" "$runner_path" "$container_workdir_path" "$cache_path" "$generators_path" "$destination_path" "$update_database" "$debug"

rm -rf "$runner_workdirs_path" && \
./"run-$mode-stop.sh" "$runner_id"
