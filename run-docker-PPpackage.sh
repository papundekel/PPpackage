runner_path="$1"
container_workdir_path="$2"
cache_path="$3"
generators_path="$4"
destination_path="$5"
update_database="$6"
debug="$7"

docker run \
    --rm \
    --interactive \
    --ulimit "nofile=1024:1048576" \
    --mount type=bind,readonly,source="/etc/passwd",destination="/etc/passwd" \
    --mount type=bind,readonly,source="/etc/group",destination="/etc/group" \
    --user "$(id -u):$(id -g)" \
    --mount type=bind,source="$runner_path",destination="/run/PPpackage-runner.sock" \
    --mount type=bind,source="$container_workdir_path",destination="/mnt/PPpackage-runner/" \
    --mount type=bind,source="$cache_path",destination="/workdir/cache" \
    --mount type=bind,source="$generators_path",destination="/workdir/generators" \
    --mount type=bind,source="$destination_path",destination="/workdir/root" \
    fackop/pppackage \
    PPpackage \
        /run/PPpackage-runner.sock \
        /mnt/PPpackage-runner \
        /workdir/cache \
        /workdir/generators \
        /workdir/root \
        $update_database \
        $debug
