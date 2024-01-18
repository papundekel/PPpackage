#!/usr/bin/env sh

cache_path_arch="tmp/cache/arch"
cache_path_conan="tmp/cache/conan"
cache_path_pp="tmp/cache/PP"

containerizer="unix://$XDG_RUNTIME_DIR/podman/podman.sock"



mkdir -p tmp/output



submanagers__arch__package=PPpackage_arch \
submanagers__arch__settings__debug=true \
submanagers__arch__settings__cache_path="$cache_path_arch" \
submanagers__arch__settings__containerizer="$containerizer" \
submanagers__arch__settings__workdir_containerizer=/ \
submanagers__arch__settings__workdir_container=/ \
\
submanagers__conan__package=PPpackage_conan \
submanagers__conan__settings__debug=true \
submanagers__conan__settings__cache_path="$cache_path_conan" \
\
submanagers__PP__package=PPpackage_PP \
submanagers__PP__settings__debug=true \
submanagers__PP__settings__cache_path="$cache_path_pp" \
submanagers__PP__settings__containerizer="$containerizer" \
python \
    -m PPpackage \
    tmp/output/root/ \
    --workdir tmp/ \
    --generators tmp/output/generators \
    --graph tmp/output/graph.dot
