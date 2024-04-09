mkdir -p tmp/output

PODMAN_COMPOSE_PROVIDER=podman-compose \
CONFIG=$(pwd)/examples/containerized/all-local/config.json \
ROOT=$(pwd)/tmp/root \
OUTPUT=$(pwd)/tmp/output \
podman compose \
    --file examples/all-local/compose.yaml \
    run \
        --rm \
        -T \
        metamanager
