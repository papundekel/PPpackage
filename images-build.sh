if [ -z "$1" ] || ([ "$1" != "docker" ] && [ "$1" != "podman" ]); then
    echo "Usage: $0 [docker | podman]"
    exit 1
fi

# "$1" build --target repository-driver-pacman --tag docker.io/fackop/pppackage-repository-driver-pacman:latest . && \
# "$1" build --target repository-driver-conan --tag docker.io/fackop/pppackage-repository-driver-conan:latest . && \
# "$1" build --target repository-driver-pp --tag docker.io/fackop/pppackage-repository-driver-pp:latest . &&\
# "$1" build --target repository-driver-aur --tag docker.io/fackop/pppackage-repository-driver-aur:latest . &&\
"$1" build --target metamanager --tag docker.io/fackop/pppackage-metamanager:latest .
