mkdir -p tmp/output
mkdir -p tmp/arch-installations
mkdir -p tmp/aur-installations

PODMAN_COMPOSE_PROVIDER=podman-compose \
WORKDIR=$(pwd)/tmp \
ARCH_INSTALLATIONS=$(pwd)/tmp/arch-installations \
AUR_INSTALLATIONS=$(pwd)/tmp/aur-installations \
podman compose \
    --file compose/all-remote/compose.yaml \
    run \
        --rm \
        -T \
        metamanager
