PODMAN_COMPOSE_PROVIDER=podman-compose \
CONFIG_PATH=$(pwd)/examples/metamanager/containerized/all-local/config.json \
ROOT=$(pwd)/tmp/root \
OUTPUT=$(pwd)/tmp/output \
podman compose \
    --file examples/metamanager/all-local/compose.yaml \
    run \
        --rm \
        -T \
        metamanager
