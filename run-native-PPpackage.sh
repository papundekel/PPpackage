runner_path="$1"
container_workdir_path="$2"
cache_path="$3"
generators_path="$4"
destination_path="$5"
update_database="$6"
debug="$7"

PPpackage "$runner_path" "$container_workdir_path" "$cache_path" "$generators_path" "$destination_path" $update_database $debug
