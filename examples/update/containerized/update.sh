"$1" run --rm \
    --security-opt label=disable \
    --mount type=bind,source="$HOME",target=/root/ \
    --env REPOSITORY=core \
    docker.io/fackop/pppackage-updater:latest \
    PPpackage.repository_driver.pacman \
    --index 0 \
    --repository-config /usr/share/doc/PPpackage/examples/update/repository-pacman.json &

"$1" run --rm \
    --security-opt label=disable \
    --mount type=bind,source="$HOME",target=/root/ \
    --env REPOSITORY=extra \
    docker.io/fackop/pppackage-updater:latest \
    PPpackage.repository_driver.pacman \
    --index 1 \
    --repository-config /usr/share/doc/PPpackage/examples/update/repository-pacman.json &

"$1" run --rm \
    --security-opt label=disable \
    --mount type=bind,source="$HOME",target=/root/ \
    docker.io/fackop/pppackage-updater:latest \
    PPpackage.repository_driver.AUR \
    --index 2 &

"$1" run --rm \
    --security-opt label=disable \
    --mount type=bind,source="$HOME",target=/root/ \
    docker.io/fackop/pppackage-updater:latest \
    PPpackage.repository_driver.conan \
    --index 3 \
    --repository-config /usr/share/doc/PPpackage/examples/update/repository-conancenter.json &

wait
