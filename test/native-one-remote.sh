#!/usr/bin/env sh

admin_token_path="tmp/admin-token"
user_token_path="tmp/user-token"
database_path="tmp/db.sqlite3"
database_url="sqlite+aiosqlite:///$database_path"
address="localhost:8880"
url="http://$address"
cache_path="tmp/cache/$1"
installations="tmp/installations/"

containerizer="unix://$XDG_RUNTIME_DIR/podman/podman.sock"



cleanup()
{
    kill -s TERM "$pid"

    rm -f "$admin_token_path"
    rm -f "$user_token_path"
    rm -f "$database_path"
    rm -rf "$installations"

    rm -rf tmp/installations

    exit "$1"
}



mkdir -p tmp/



./init_database.py "$database_url" > "$admin_token_path" || cleanup 10



mkdir -p "$installations"



CACHE_PATH="$cache_path" \
CONTAINERIZER="$containerizer" \
WORKDIR__CONTAINERIZER_PATH="tmp/" \
WORKDIR__CONTAINER_PATH="tmp/" \
SUBMANAGER_PACKAGE="PPpackage_$1" \
DATABASE_URL="$database_url" \
INSTALLATIONS_PATH="$installations" \
hypercorn \
    PPpackage_submanager.server:server \
    --bind "$address" \
    &
pid=$!



while :
do
	if curl "$url" 2>/dev/null >/dev/null
    then
		break
	fi

    echo "Waiting for submanagers to start..."

    sleep 1
done



./update_database.py "$url" "$admin_token_path" || cleanup 20
./create_user.py "$url" "$admin_token_path" > "$user_token_path" || cleanup 30



mkdir -p tmp/output


env \
"submanagers__${1}__url"="$url" \
"submanagers__${1}__token_path"="$user_token_path" \
python \
    -m PPpackage \
    tmp/output/root/ \
    --workdir tmp/ \
    --generators tmp/output/generators \
    --graph tmp/output/graph.dot



cleanup 0
