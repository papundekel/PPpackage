#!/usr/bin/env sh

address_archlinux_core="localhost:8880"
address_archlinux_extra="localhost:8881"
address_AUR="localhost:8882"
address_conan_conancenter="localhost:8883"
address_PP="localhost:8884"



mkdir -p tmp/
mkdir -p tmp/output/



CONFIG="$(pwd)/example/native/all-remote/archlinux-core/config.json"
hypercorn \
    PPpackage_submanager.server:server \
    --bind "$address_archlinux_core" \
    &
pid_archlinux_core=$!

CONFIG="$(pwd)/example/native/all-remote/archlinux-extra/config.json"
hypercorn \
    PPpackage_submanager.server:server \
    --bind "$address_archlinux_extra" \
    &
pid_archlinux_extra=$!

CONFIG="$(pwd)/example/native/all-remote/AUR/config.json"
hypercorn \
    PPpackage_submanager.server:server \
    --bind "$address_AUR" \
    &
pid_AUR=$!

CONFIG="$(pwd)/example/native/all-remote/conan-conancenter/config.json"
hypercorn \
    PPpackage_submanager.server:server \
    --bind "$address_conan_conancenter" \
    &
pid_conan_conancenter=$!

CONFIG="$(pwd)/example/native/all-remote/PP/config.json"
hypercorn \
    PPpackage_submanager.server:server \
    --bind "$address_PP" \
    &
pid_PP=$!



while :
do
	if \
        curl "http://$address_archlinux_core" 2>/dev/null >/dev/null && \
        curl "http://$address_archlinux_extra" 2>/dev/null >/dev/null && \
        curl "http://$address_AUR" 2>/dev/null >/dev/null && \
        curl "http://$address_conan_conancenter" 2>/dev/null >/dev/null && \
        curl "http://$address_PP" 2>/dev/null >/dev/null
    then
		break
	fi

    echo "Waiting for repositories to start..."

    sleep 1
done



python \
    -m PPpackage \
    tmp/root/ \
    --config example/native/all-remote/config.json \
    --workdir /tmp \
    --generators tmp/output/generators \
    --graph tmp/output/graph.dot



kill -s TERM $pid_archlinux_core
kill -s TERM $pid_archlinux_extra
kill -s TERM $pid_AUR
kill -s TERM $pid_conan_conancenter
kill -s TERM $pid_PP
