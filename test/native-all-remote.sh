#!/usr/bin/env sh

admin_token_path_arch="tmp/admin-token-arch"
admin_token_path_conan="tmp/admin-token-conan"
admin_token_path_pp="tmp/admin-token-pp"

user_token_path_arch="tmp/user-token-arch"
user_token_path_conan="tmp/user-token-conan"
user_token_path_pp="tmp/user-token-pp"

database_path_arch="tmp/arch-db.sqlite3"
database_path_conan="tmp/conan-db.sqlite3"
database_path_pp="tmp/pp-db.sqlite3"

database_url_arch="sqlite+aiosqlite:///$database_path_arch"
database_url_conan="sqlite+aiosqlite:///$database_path_conan"
database_url_pp="sqlite+aiosqlite:///$database_path_pp"

address_arch="localhost:8880"
address_conan="localhost:8881"
address_pp="localhost:8882"

url_arch="http://$address_arch"
url_conan="http://$address_conan"
url_pp="http://$address_pp"

cache_path_arch="tmp/cache/arch"
cache_path_conan="tmp/cache/conan"
cache_path_pp="tmp/cache/PP"

installations_arch="tmp/installations/arch"
installations_conan="tmp/installations/conan"
installations_pp="tmp/installations/PP"

containerizer="unix://$XDG_RUNTIME_DIR/podman/podman.sock"


cleanup()
{
    kill -s TERM $pid_arch
    kill -s TERM $pid_conan
    kill -s TERM $pid_pp

    rm -f "$admin_token_path_arch" "$admin_token_path_conan" "$admin_token_path_pp"

    rm -f "$user_token_path_arch" "$user_token_path_conan" "$user_token_path_pp"

    rm -f "$database_path_arch" "$database_path_conan" "$database_path_pp"

    rm -rf "$installations_arch" "$installations_conan" "$installations_pp"
    rm -rf tmp/installations
}



./init_database.py "$database_url_arch" > "$admin_token_path_arch" || (cleanup; exit 10)
./init_database.py "$database_url_conan" > "$admin_token_path_conan" || (cleanup; exit 11)
./init_database.py "$database_url_pp" > "$admin_token_path_pp" || (cleanup; exit 12)



mkdir -p "$installations_arch" "$installations_conan" "$installations_pp"



DEBUG=true \
CACHE_PATH="$cache_path_arch" \
CONTAINERIZER="$containerizer" \
WORKDIR_CONTAINERIZER="/" \
WORKDIR_CONTAINER="/" \
SUBMANAGER_PACKAGE=PPpackage_arch \
DATABASE_URL="$database_url_arch" \
INSTALLATIONS_PATH="$installations_arch" \
hypercorn \
    PPpackage_submanager.server:server \
    --bind "$address_arch" \
    &
pid_arch=$!

DEBUG=true \
CACHE_PATH="$cache_path_conan" \
SUBMANAGER_PACKAGE=PPpackage_conan \
DATABASE_URL="$database_url_conan" \
INSTALLATIONS_PATH="$installations_conan" \
hypercorn \
    PPpackage_submanager.server:server \
    --bind "$address_conan" \
    &
pid_conan=$!

DEBUG=true \
CACHE_PATH="$cache_path_pp" \
CONTAINERIZER="$containerizer" \
SUBMANAGER_PACKAGE=PPpackage_PP \
DATABASE_URL="$database_url_pp" \
INSTALLATIONS_PATH="$installations_pp" \
hypercorn \
    PPpackage_submanager.server:server \
    --bind "$address_pp" \
    &
pid_pp=$!



while :
do
	if \
        curl "$url_arch" 2>/dev/null >/dev/null && \
        curl "$url_conan" 2>/dev/null >/dev/null && \
        curl "$url_pp" 2>/dev/null >/dev/null
    then
		break
	fi

    sleep 1
done



curl -f -X POST "$url_arch/update-database" > /dev/null 2>/dev/null || (cleanup; exit 20)
curl -f -X POST "$url_conan/update-database" > /dev/null 2>/dev/null || (cleanup; exit 21)
curl -f -X POST "$url_pp/update-database" > /dev/null 2>/dev/null || (cleanup; exit 22)



./create_user.py "$url_arch" "$admin_token_path_arch" > "$user_token_path_arch" || (cleanup; exit 30)
./create_user.py "$url_conan" "$admin_token_path_conan" > "$user_token_path_conan" || (cleanup; exit 31)
./create_user.py "$url_pp" "$admin_token_path_pp" > "$user_token_path_pp" || (cleanup; exit 32)



mkdir -p tmp/output



submanagers__arch__url="$url_arch" \
submanagers__arch__token_path="$user_token_path_arch" \
submanagers__conan__url="$url_conan" \
submanagers__conan__token_path="$user_token_path_conan" \
submanagers__PP__url="$url_pp" \
submanagers__PP__token_path="$user_token_path_pp" \
python \
    -m PPpackage \
    tmp/output/root/ \
    --workdir tmp/ \
    --generators tmp/output/generators \
    --graph tmp/output/graph.dot



cleanup
