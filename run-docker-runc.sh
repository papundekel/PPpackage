runc_path="$1"
debug="$2"
name="fackop-pppackage-runner"

docker run \
    --privileged \
    --detach \
    --user "$(id -u):$(id -g)" \
    --name "$name" \
    --mount type=bind,source="$runc_path/run",destination="/workdir/PPpackage-runner/run" \
    --mount type=bind,source="$runc_path/containers",destination="/workdir/PPpackage-runner/containers" \
    fackop/pppackage-runner PPpackage-runner PPpackage-runner/ $debug > /dev/null

echo "$name"
