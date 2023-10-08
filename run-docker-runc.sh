runc_path="$1"
debug="$2"
name="fackop-pppackage-runc"

docker run \
    --privileged \
    --detach \
    --user "$(id -u):$(id -g)" \
    --name "$name" \
    --mount type=bind,source="$runc_path/run",destination="/workdir/PPpackage-runc/run" \
    --mount type=bind,source="$runc_path/containers",destination="/workdir/PPpackage-runc/containers" \
    fackop/pppackage-runc PPpackage-runc PPpackage-runc/ $debug > /dev/null

echo "$name"
