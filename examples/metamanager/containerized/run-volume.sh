PPPACKAGE_HOME="$2" "$1" compose \
    --file examples/metamanager/containerized/compose-volume.yaml \
    run \
        --rm \
        -T \
        metamanager
