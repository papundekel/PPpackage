if [ -z "$1" ] || ([ "$1" != "docker" ] && [ "$1" != "podman" ]); then
    echo "Usage: $0 [docker | podman]"
    exit 1
fi

"$1" run --rm \
    --security-opt label=disable \
    --mount type=bind,source="$HOME",target=/root/ \
    --env REPOSITORY=core \
    docker.io/fackop/pppackage-updater:latest \
    PPpackage.repository_driver.pacman \
    archlinux-core \
    --repository-config /usr/share/doc/PPpackage/examples/update/repository-pacman.json

"$1" run --rm \
    --security-opt label=disable \
    --mount type=bind,source="$HOME",target=/root/ \
    --env REPOSITORY=extra \
    docker.io/fackop/pppackage-updater:latest \
    PPpackage.repository_driver.pacman \
    archlinux-extra \
    --repository-config /usr/share/doc/PPpackage/examples/update/repository-pacman.json &

"$1" run --rm \
    --security-opt label=disable \
    --mount type=bind,source="$HOME",target=/root/ \
    docker.io/fackop/pppackage-updater:latest \
    PPpackage.repository_driver.AUR \
    AUR &

"$1" run --rm \
    --security-opt label=disable \
    --mount type=bind,source="$HOME",target=/root/ \
    docker.io/fackop/pppackage-updater:latest \
    PPpackage.repository_driver.conan \
    conancenter \
    --repository-config /usr/share/doc/PPpackage/examples/update/repository-conancenter.json &

wait
