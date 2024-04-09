if [ -z "$1" ] || ([ "$1" != "docker" ] && [ "$1" != "podman" ]); then
    echo "Usage: $0 [docker | podman]"
    exit 1
fi

"$1" build --target submanager-db-init --tag docker.io/fackop/pppackage-submanager-db-init:latest . && \
"$1" build --target submanager-create-user --tag docker.io/fackop/pppackage-submanager-create-user:latest . && \
"$1" build --target submanager-arch --tag docker.io/fackop/PPpackage-pacman:latest . && \
"$1" build --target submanager-conan --tag docker.io/fackop/pppackage-conan:latest . && \
"$1" build --target submanager-pp --tag docker.io/fackop/pppackage-pp:latest . &&\
"$1" build --target submanager-aur --tag docker.io/fackop/pppackage-aur:latest . &&\
"$1" build --target metamanager --tag docker.io/fackop/pppackage:latest .
