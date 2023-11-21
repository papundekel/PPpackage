runner_path="$1"
machine_id="$2"
debug="$3"

podman run \
    --rm \
    --mount type=bind,source="$runner_path",destination="/run/PPpackage-runner.sock" \
    docker-daemon:docker.io/fackop/pppackage-runner:latest \
    ./run-init.py \
        /run/PPpackage-runner.sock \
        "$machine_id" \
        "$debug"
