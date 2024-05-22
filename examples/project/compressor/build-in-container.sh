if [ -z "$1" ] || ([ "$1" != "docker" ] && [ "$1" != "podman" ]); then
    echo "Usage: $0 [docker | podman]"
    exit 1
fi

project_root="$PWD/examples/project/compressor"

mkdir -p "$project_root/build/output"

"$1" run --rm \
    --mount type=bind,source="$project_root/build/generators",target=/mnt/generators \
    --mount type=bind,source="$project_root/compressor",target=/mnt/source \
    --mount type=bind,source="$project_root/build/output",target=/mnt/output \
    --mount type=bind,source="$project_root/build.sh",target=/mnt/build.sh \
    --rootfs "$project_root/build/root" \
    bash /mnt/build.sh
