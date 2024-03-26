mkdir -p tmp/output

PODMAN_COMPOSE_PROVIDER=podman-compose \
WORKDIR=$(pwd)/tmp \
ARCH_INSTALLATIONS=$(pwd)/tmp/arch-installations \
AUR_INSTALLATIONS=$(pwd)/tmp/aur-installations \
podman compose \
    --file compose/all-remote/compose.yaml \
    run \
        --rm \
        db-init-arch && \
\
PODMAN_COMPOSE_PROVIDER=podman-compose \
WORKDIR=$(pwd)/tmp \
ARCH_INSTALLATIONS=$(pwd)/tmp/arch-installations \
AUR_INSTALLATIONS=$(pwd)/tmp/aur-installations \
podman compose \
    --file compose/all-remote/compose.yaml \
    run \
        --rm \
        db-init-conan && \
\
PODMAN_COMPOSE_PROVIDER=podman-compose \
WORKDIR=$(pwd)/tmp \
ARCH_INSTALLATIONS=$(pwd)/tmp/arch-installations \
AUR_INSTALLATIONS=$(pwd)/tmp/aur-installations \
podman compose \
    --file compose/all-remote/compose.yaml \
    run \
        --rm \
        db-init-pp && \
\
PODMAN_COMPOSE_PROVIDER=podman-compose \
WORKDIR=$(pwd)/tmp \
ARCH_INSTALLATIONS=$(pwd)/tmp/arch-installations \
AUR_INSTALLATIONS=$(pwd)/tmp/aur-installations \
podman compose \
    --file compose/all-remote/compose.yaml \
    run \
        --rm \
        db-init-aur && \
\
PODMAN_COMPOSE_PROVIDER=podman-compose \
WORKDIR=$(pwd)/tmp \
ARCH_INSTALLATIONS=$(pwd)/tmp/arch-installations \
AUR_INSTALLATIONS=$(pwd)/tmp/aur-installations \
podman compose \
    --file compose/all-remote/compose.yaml \
    run \
        --rm \
        create-user-arch && \
\
PODMAN_COMPOSE_PROVIDER=podman-compose \
WORKDIR=$(pwd)/tmp \
ARCH_INSTALLATIONS=$(pwd)/tmp/arch-installations \
AUR_INSTALLATIONS=$(pwd)/tmp/aur-installations \
podman compose \
    --file compose/all-remote/compose.yaml \
    run \
        --rm \
        create-user-conan && \
\
PODMAN_COMPOSE_PROVIDER=podman-compose \
WORKDIR=$(pwd)/tmp \
ARCH_INSTALLATIONS=$(pwd)/tmp/arch-installations \
AUR_INSTALLATIONS=$(pwd)/tmp/aur-installations \
podman compose \
    --file compose/all-remote/compose.yaml \
    run \
        --rm \
        create-user-pp
\
PODMAN_COMPOSE_PROVIDER=podman-compose \
WORKDIR=$(pwd)/tmp \
ARCH_INSTALLATIONS=$(pwd)/tmp/arch-installations \
AUR_INSTALLATIONS=$(pwd)/tmp/aur-installations \
podman compose \
    --file compose/all-remote/compose.yaml \
    run \
        --rm \
        create-user-aur
