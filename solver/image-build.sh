if [ -z "$1" ] || ([ "$1" != "docker" ] && [ "$1" != "podman" ]); then
    echo "Usage: $0 [docker | podman]"
    exit 1
fi

"$1" build --target solver --tag docker.io/fackop/pppackage-solver:latest .
