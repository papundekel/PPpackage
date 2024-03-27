#!/usr/bin/env sh

admin_token_path_arch="tmp/admin-token-arch"
admin_token_path_conan="tmp/admin-token-conan"
admin_token_path_pp="tmp/admin-token-pp"
admin_token_path_aur="tmp/admin-token-aur"

user_token_path_arch="tmp/user-token-arch"
user_token_path_conan="tmp/user-token-conan"
user_token_path_pp="tmp/user-token-pp"
user_token_path_aur="tmp/user-token-aur"

database_path_arch="tmp/arch-db.sqlite3"
database_path_conan="tmp/conan-db.sqlite3"
database_path_pp="tmp/pp-db.sqlite3"
database_path_aur="tmp/aur-db.sqlite3"

database_url_arch="sqlite+aiosqlite:///$database_path_arch"
database_url_conan="sqlite+aiosqlite:///$database_path_conan"
database_url_pp="sqlite+aiosqlite:///$database_path_pp"
database_url_aur="sqlite+aiosqlite:///$database_path_aur"

address_arch="localhost:8880"
address_conan="localhost:8881"
address_pp="localhost:8882"
address_aur="localhost:8883"

url_arch="http://$address_arch"
url_conan="http://$address_conan"
url_pp="http://$address_pp"
url_aur="http://$address_aur"

cache_path_arch="tmp/cache/arch"
cache_path_conan="tmp/cache/conan"
cache_path_pp="tmp/cache/PP"
cache_path_aur="tmp/cache/AUR"

installations_arch="tmp/installations/arch"
installations_conan="tmp/installations/conan"
installations_pp="tmp/installations/PP"
installations_aur="tmp/installations/AUR"

containerizer="unix://$XDG_RUNTIME_DIR/podman/podman.sock"


cleanup()
{
    kill -s TERM $pid_arch
    kill -s TERM $pid_conan
    kill -s TERM $pid_pp
    kill -s TERM $pid_aur

    
    rm -f \
        "$admin_token_path_arch" \
        "$admin_token_path_conan" \
        "$admin_token_path_pp" \
        "$admin_token_path_aur"

    rm -f \
        "$user_token_path_arch" \
        "$user_token_path_conan" \
        "$user_token_path_pp" \
        "$user_token_path_aur"

    rm -f \
        "$database_path_arch" \
        "$database_path_conan" \
        "$database_path_pp" \
        "$database_path_aur"

    rm -rf \
        "$installations_arch" \
        "$installations_conan" \
        "$installations_pp" \
        "$installations_aur"


    rm -rf tmp/installations

    exit "$1"
}



mkdir -p tmp/



./init_database.py "$database_url_arch" > "$admin_token_path_arch" || cleanup 10
./init_database.py "$database_url_conan" > "$admin_token_path_conan" || cleanup 11
./init_database.py "$database_url_pp" > "$admin_token_path_pp" || cleanup 12
./init_database.py "$database_url_aur" > "$admin_token_path_aur" || cleanup 12



mkdir -p \
    "$installations_arch" \
    "$installations_conan" \
    "$installations_pp" \
    "$installations_aur"



CACHE_PATH="$cache_path_arch" \
CONTAINERIZER="$containerizer" \
WORKDIR__CONTAINERIZER_PATH="tmp/" \
WORKDIR__CONTAINER_PATH="tmp/" \
SUBMANAGER_PACKAGE=PPpackage_arch \
DATABASE_URL="$database_url_arch" \
INSTALLATIONS_PATH="$installations_arch" \
BUILD_CONTEXT_WORKDIR_PATH="tmp/" \
hypercorn \
    PPpackage_submanager.server:server \
    --bind "$address_arch" \
    &
pid_arch=$!

CACHE_PATH="$cache_path_conan" \
SUBMANAGER_PACKAGE=PPpackage_conan \
DATABASE_URL="$database_url_conan" \
INSTALLATIONS_PATH="$installations_conan" \
BUILD_CONTEXT_WORKDIR_PATH="tmp/" \
hypercorn \
    PPpackage_submanager.server:server \
    --bind "$address_conan" \
    &
pid_conan=$!

CACHE_PATH="$cache_path_pp" \
CONTAINERIZER="$containerizer" \
SUBMANAGER_PACKAGE=PPpackage_PP \
DATABASE_URL="$database_url_pp" \
INSTALLATIONS_PATH="$installations_pp" \
BUILD_CONTEXT_WORKDIR_PATH="tmp/" \
hypercorn \
    PPpackage_submanager.server:server \
    --bind "$address_pp" \
    &
pid_pp=$!

CACHE_PATH="$cache_path_aur" \
CONTAINERIZER="$containerizer" \
WORKDIR__CONTAINERIZER_PATH="tmp/" \
WORKDIR__CONTAINER_PATH="tmp/" \
SUBMANAGER_PACKAGE=PPpackage_AUR \
DATABASE_URL="$database_url_aur" \
INSTALLATIONS_PATH="$installations_aur" \
BUILD_CONTEXT_WORKDIR_PATH="tmp/" \
hypercorn \
    PPpackage_submanager.server:server \
    --bind "$address_aur" \
    &
pid_aur=$!



while :
do
	if \
        curl "$url_arch" 2>/dev/null >/dev/null && \
        curl "$url_conan" 2>/dev/null >/dev/null && \
        curl "$url_pp" 2>/dev/null >/dev/null && \
        curl "$url_aur" 2>/dev/null >/dev/null
    then
		break
	fi

    echo "Waiting for submanagers to start..."

    sleep 1
done



./update_database.py "$url_arch" "$admin_token_path_arch" || cleanup 20
./update_database.py "$url_conan" "$admin_token_path_conan" || cleanup 21
./update_database.py "$url_pp" "$admin_token_path_pp" || cleanup 22
./update_database.py "$url_aur" "$admin_token_path_aur" || cleanup 22



./create_user.py "$url_arch" "$admin_token_path_arch" > "$user_token_path_arch" || cleanup 30
./create_user.py "$url_conan" "$admin_token_path_conan" > "$user_token_path_conan" || cleanup 31
./create_user.py "$url_pp" "$admin_token_path_pp" > "$user_token_path_pp" || cleanup 32
./create_user.py "$url_aur" "$admin_token_path_aur" > "$user_token_path_aur" || cleanup 32



mkdir -p tmp/output



submanagers__arch__url="$url_arch" \
submanagers__arch__token_path="$user_token_path_arch" \
submanagers__conan__url="$url_conan" \
submanagers__conan__token_path="$user_token_path_conan" \
submanagers__PP__url="$url_pp" \
submanagers__PP__token_path="$user_token_path_pp" \
submanagers__AUR__url="$url_aur" \
submanagers__AUR__token_path="$user_token_path_aur" \
python \
    -m PPpackage \
    tmp/output/root/ \
    --workdir tmp/ \
    --generators tmp/output/generators \
    --graph tmp/output/graph.dot



cleanup 0
