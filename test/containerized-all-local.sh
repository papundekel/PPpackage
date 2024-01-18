mkdir -p tmp/output

PODMAN_COMPOSE_PROVIDER=podman-compose \
WORKDIR=$(pwd)/tmp \
podman compose \
    --file compose/all-local/compose.yaml \
    run \
        --rm \
        -T \
        metamanager
