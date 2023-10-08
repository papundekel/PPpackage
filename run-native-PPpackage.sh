cache_path="$1"
generators_path="$2"
runc_path="$3"
container_relative_path="$4"
debug="$5"

PPpackage "$cache_path" "$generators_path" "$runc_path/run/PPpackage-runc.sock" "$runc_path/containers/$container_relative_path" root/ $debug
