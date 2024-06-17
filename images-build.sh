if [ -z "$1" ] || ([ "$1" != "docker" ] && [ "$1" != "podman" ]); then
    echo "Usage: $0 [docker | podman]"
    exit 1
fi

./solver/image-build.sh "$1" && \
"$1" build --target updater --tag docker.io/fackop/pppackage-updater:latest . && \
"$1" build --target metamanager --tag docker.io/fackop/pppackage-metamanager:latest .
