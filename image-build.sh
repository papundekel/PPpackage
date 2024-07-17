usage="Usage: $0 [docker | podman] [solver | metamanager | updater]"

if [ -z "$1" ] || ([ "$1" != "docker" ] && [ "$1" != "podman" ]); then
    echo "$usage"
    exit 1
fi

if [ -z "$2" ] || ([ "$2" != "solver" ] && [ "$2" != "metamanager" ] && [ "$2" != "updater" ]); then
    echo "$usage"
    exit 2
fi

"$1" build --target "$2" --tag "docker.io/fackop/pppackage-$2:latest" .
