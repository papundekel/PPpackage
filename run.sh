mkdir -p tmp/cache tmp/generators tmp/root tmp/inter

docker run \
    --rm \
    --ulimit "nofile=1024:1048576" \
    --mount type=bind,source="$(pwd)"/tmp/cache,destination=/workdir/tmp/cache \
    --mount type=bind,source="$(pwd)"/tmp/generators,destination=/workdir/tmp/generators \
    --mount type=bind,source="$(pwd)"/tmp/root,destination=/workdir/tmp/root \
    --mount type=bind,source="$(pwd)"/tmp/inter,destination=/workdir/tmp/inter \
    pppackage \
    ./manager.sh PPpackage requirements.json generators.json tmp/generators tmp/root
