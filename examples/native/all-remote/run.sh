#!/usr/bin/env sh

address_archlinux_core="localhost:8880"
address_archlinux_extra="localhost:8881"
address_AUR="localhost:8882"
address_conancenter="localhost:8883"



CONFIG_PATH="$PWD/examples/native/all-remote/archlinux-core/config.json" \
hypercorn \
    PPpackage.repository_driver.server.server:server \
    --bind "$address_archlinux_core" \
    &
pid_archlinux_core=$!

CONFIG_PATH="$PWD/examples/native/all-remote/archlinux-extra/config.json" \
hypercorn \
    PPpackage.repository_driver.server.server:server \
    --bind "$address_archlinux_extra" \
    &
pid_archlinux_extra=$!

CONFIG_PATH="$PWD/examples/native/all-remote/AUR/config.json" \
hypercorn \
    PPpackage.repository_driver.server.server:server \
    --bind "$address_AUR" \
    &
pid_AUR=$!

CONFIG_PATH="$PWD/examples/native/all-remote/conancenter/config.json" \
hypercorn \
    PPpackage.repository_driver.server.server:server \
    --bind "$address_conancenter" \
    &
pid_conancenter=$!



while :
do
	if \
        curl "http://$address_archlinux_core" 2>/dev/null >/dev/null && \
        curl "http://$address_archlinux_extra" 2>/dev/null >/dev/null && \
        curl "http://$address_AUR" 2>/dev/null >/dev/null && \
        curl "http://$address_conancenter" 2>/dev/null >/dev/null
    then
		break
	fi

    echo "Waiting for repositories to start..."

    sleep 1
done



python \
    -m PPpackage.metamanager \
    tmp/root/ \
    --config examples/native/all-remote/config.json \
    --generators tmp/output/generators \
    --graph tmp/output/graph.dot



kill -s TERM $pid_archlinux_core
kill -s TERM $pid_archlinux_extra
kill -s TERM $pid_AUR
kill -s TERM $pid_conancenter
