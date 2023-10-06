#!/usr/bin/env sh

tmp_path="$1/"
daemon_socket_path="$2/"
daemon_workdir_path="$3/"
destination_relative_path="$4/"
debug="$5"

managers_path="./"
cache_path="$tmp_path/cache/"
generators_path="$tmp_path/generators/"

./PPpackage.py "$managers_path" "$cache_path" "$generators_path" "$daemon_socket_path" "$daemon_workdir_path" "$destination_relative_path" --update-database $debug
