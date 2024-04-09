mkdir -p tmp/output

PODMAN_COMPOSE_PROVIDER=podman-compose \
CONFIG=$(pwd)/example/containerized/all-remote/config.json \
CONFIG_ARCHLINUX_CORE=$(pwd)/example/containerized/all-remote/archlinux-core/config.json \
CONFIG_ARCHLINUX_EXTRA=$(pwd)/example/containerized/all-remote/archlinux-extra/config.json \
CONFIG_AUR=$(pwd)/example/containerized/all-remote/aur/config.json \
CONFIG_CONAN_CONANCENTER=$(pwd)/example/containerized/all-remote/conan-conancenter/config.json \
CONFIG_PP=$(pwd)/example/containerized/all-remote/pp/config.json \
ROOT=$(pwd)/tmp/root \
OUTPUT=$(pwd)/tmp/output \
podman compose \
    --file example/all-remote/compose.yaml \
    run \
        --rm \
        -T \
        metamanager
