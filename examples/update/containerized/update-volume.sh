"$1" run --rm \
    --mount type=volume,source="$2",target=/root/ \
    --mount type=bind,source="$PWD/examples/update/repository-pacman.json",target=/mnt/repository.json \
    --env REPOSITORY=core \
    docker.io/fackop/pppackage-updater:latest \
    PPpackage.repository_driver.pacman \
    --index 0 \
    --repository-config /mnt/repository.json &

"$1" run --rm \
    --mount type=volume,source="$2",target=/root/ \
    --mount type=bind,source="$PWD/examples/update/repository-pacman.json",target=/mnt/repository.json \
    --env REPOSITORY=extra \
    docker.io/fackop/pppackage-updater:latest \
    PPpackage.repository_driver.pacman \
    --index 1 \
    --repository-config /mnt/repository.json &

"$1" run --rm \
    --mount type=volume,source="$2",target=/root/ \
    docker.io/fackop/pppackage-updater:latest \
    PPpackage.repository_driver.AUR \
    --index 2 &

"$1" run --rm \
    --mount type=volume,source="$2",target=/root/ \
    --mount type=bind,source="$PWD/examples/update/repository-conancenter.json",target=/mnt/repository.json \
    docker.io/fackop/pppackage-updater:latest \
    PPpackage.repository_driver.conan \
    --index 3 \
    --repository-config /mnt/repository.json &

wait
