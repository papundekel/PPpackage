runc_path="$1"
debug="$2"
name="fackop-pppackage-runner"

mkdir -p "$runc_path/storage"

podman run \
    --privileged \
    --detach \
    --name "$name" \
    --mount type=bind,source="$runc_path/run",destination="/workdir/PPpackage-runner/run" \
    --mount type=bind,source="$runc_path/containers",destination="/workdir/PPpackage-runner/containers" \
    --mount type=bind,source="$runc_path/storage",destination="/var/lib/containers" \
    fackop/pppackage-runner PPpackage-runner PPpackage-runner/ $debug > /dev/null

echo "$name"
