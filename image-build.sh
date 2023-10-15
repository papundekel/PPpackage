docker build --tag fackop/pppackage --file images/PPpackage/Dockerfile ./ &&\
podman build --tag fackop/pppackage-runner --file images/PPpackage-runner/Dockerfile ./
