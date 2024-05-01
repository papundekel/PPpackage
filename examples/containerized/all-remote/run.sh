PODMAN_COMPOSE_PROVIDER=podman-compose \
CONFIG_PATH=$(pwd)/examples/containerized/all-remote/config.json \
CONFIG_ARCHLINUX_CORE=$(pwd)/examples/containerized/all-remote/archlinux-core/config.json \
CONFIG_ARCHLINUX_EXTRA=$(pwd)/examples/containerized/all-remote/archlinux-extra/config.json \
CONFIG_AUR=$(pwd)/examples/containerized/all-remote/aur/config.json \
CONFIG_CONANCENTER=$(pwd)/examples/containerized/all-remote/conancenter/config.json \
CONFIG_PP=$(pwd)/examples/containerized/all-remote/pp/config.json \
ROOT=$(pwd)/tmp/root \
OUTPUT=$(pwd)/tmp/output \
podman compose \
    --file examples/all-remote/compose.yaml \
    run \
        --rm \
        -T \
        metamanager
