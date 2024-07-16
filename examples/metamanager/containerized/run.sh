if [ -z "$1" ] || ([ "$1" != "docker" ] && [ "$1" != "podman" ]); then
    echo "Usage: $0 [docker | podman]"
    exit 1
fi

mkdir -p tmp/output tmp/root

"$1" compose \
    --file examples/metamanager/containerized/compose.yaml \
    run \
        --rm \
        -T \
        metamanager
