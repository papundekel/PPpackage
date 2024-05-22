podman compose \
    --file examples/metamanager/containerized/compose.yaml \
    run \
        --rm \
        -T \
        metamanager
