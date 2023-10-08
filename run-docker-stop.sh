runc_id="$1"

docker container stop "$runc_id" && \
docker logs "$runc_id" && \
docker container rm "$runc_id"
