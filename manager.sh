#!/usr/bin/env sh

tmp_path="tmp/"
cache_path="$tmp_path/cache/"
inter_path="$tmp_path/inter/"


mkdir -p "$tmp_path" "$cache_path" "$inter_path"
rm -f "$inter_path/lockfile-versions.json" "$inter_path/lockfile-versions-and-generators.json" "$inter_path/lockfile-product-ids.json" "$inter_path/products.json"
./PPpackage_arch.py update_db "$cache_path" && \
"./PPpackage_$1.py" resolve "$cache_path" <"$2" | json_reformat >"$inter_path/lockfile-versions.json" && \
"./combine-lockfile-generators.py" "$inter_path/lockfile-versions.json" "$3" | json_reformat >"$inter_path/lockfile-versions-and-generators.json" && \
"./PPpackage_$1.py" fetch "$cache_path" "$4" <"$inter_path/lockfile-versions-and-generators.json" | json_reformat >"$inter_path/lockfile-product-ids.json" && \
"./combine-lockfile-product-ids.py" "$inter_path/lockfile-versions.json" "$inter_path/lockfile-product-ids.json" | json_reformat >"$inter_path/products.json" && \
"./PPpackage_$1.py" install "$cache_path" "$5" <"$inter_path/products.json"
