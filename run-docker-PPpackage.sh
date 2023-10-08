cache_path="$1"
generators_path="$2"
runc_path="$3"
container_relative_path="$4"
debug="$5"

docker run \
    --rm \
    --interactive \
    --ulimit "nofile=1024:1048576" \
    --mount type=bind,readonly,source="/etc/passwd",destination="/etc/passwd" \
    --mount type=bind,readonly,source="/etc/group",destination="/etc/group" \
    --user "$(id -u):$(id -g)" \
    --mount type=bind,source="$cache_path",destination="/workdir/tmp/cache" \
    --mount type=bind,source="$generators_path",destination="/workdir/tmp/generators" \
    --mount type=bind,source="$runc_path/run/PPpackage-runc.sock",destination="/run/PPpackage-runc.sock" \
    --mount type=bind,source="$runc_path/containers/$container_relative_path",destination="/mnt/PPpackage-runc/" \
    fackop/pppackage PPpackage tmp/cache tmp/generators /run/PPpackage-runc.sock /mnt/PPpackage-runc/ root/ $debug
