run_path="$1"
workdirs_path="$2"
debug="$3"
name="fackop-pppackage-runner"

podman volume create --ignore podman-store > /dev/null && \
\
podman run \
    --privileged \
    --detach \
    --name "$name" \
    --mount type=bind,source="$run_path",destination="/run" \
    --mount type=bind,source="$workdirs_path",destination="/root/workdirs" \
    --mount type=volume,source=podman-store,destination=/var/lib/containers \
    fackop/pppackage-runner PPpackage-runner /run /root/workdirs $debug > /dev/null

echo "$name"
