runner_id="$1"

podman container stop "$runner_id" && \
podman logs "$runner_id" && \
podman container rm "$runner_id"
