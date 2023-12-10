if [ -z "$1" ]; then
    echo "Usage: $0 <containerizer>"
    exit 1
fi

containerizer="$1"

"$containerizer" build --tag fackop/pppackage-arch --file images/PPpackage-arch/Dockerfile ./ && \
"$containerizer" build --tag fackop/pppackage-conan --file images/PPpackage-conan/Dockerfile ./ && \
"$containerizer" build --tag fackop/pppackage-pp --file images/PPpackage-PP/Dockerfile ./
