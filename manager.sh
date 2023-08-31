#!/usr/bin/env sh

tmp_path="$1/"
debug="$2"

managers_path="./"
cache_path="$tmp_path/cache/"
generators_path="$tmp_path/generators/"
destination_path="$tmp_path/root/"
input_path="$tmp_path/input/"

./PPpackage_arch.py update-db "$cache_path" && \
./PPpackage.py $debug "$managers_path" "$cache_path" "$generators_path" "$destination_path" <"$input_path/input.json"
