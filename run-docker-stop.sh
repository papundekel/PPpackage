runc_id="$1"

podman container stop "$runc_id" && \
podman logs "$runc_id" && \
podman container rm "$runc_id"
