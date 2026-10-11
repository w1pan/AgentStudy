#!/usr/bin/env bash
# Run on the existing ECS instance after uploading both release files to /root.
set -Eeuo pipefail
umask 077
archive=/root/qingheng-ecs-20261011-204641-310.tar.gz
expected=b8c09fcf131698454a81e5b4a83d7fd8da967d7b34c9d580e75650a0e98fb779
root=/root/qingheng
cd "$root/deploy/ecs"
printf '%s  %s\n' "$expected" "$archive" | sha256sum --check -
docker compose config --quiet
test -f nginx.conf
stamp=$(date +%Y%m%d-%H%M%S)-$$
backup="/root/qingheng-backups/release-$stamp"
mkdir -p "$backup"

trap 'echo "Update failed. Backup directory: $backup. Check output before retrying; do not delete database volumes." >&2' ERR

# Keep exact images used by the existing containers, not merely latest tags.
for service in api web; do
    container=$(docker compose ps -q "$service")
    test -n "$container"
    old_image=$(docker inspect --format '{{.Image}}' "$container")
    docker image tag "$old_image" "qingheng-$service:before-$stamp"
done
cat > "$backup/rollback.yaml" <<EOF
services:
  api:
    image: qingheng-api:before-$stamp
  web:
    image: qingheng-web:before-$stamp
EOF
# pg_dump takes a consistent snapshot while the current app keeps running.
docker compose exec -T db pg_dump -U qingheng -d qingheng -Fc > "$backup/database.dump"
docker compose exec -T db pg_restore --list < "$backup/database.dump" > "$backup/database-list.txt"
test -s "$backup/database-list.txt"
tar -czf "$backup/source-before.tar.gz" -C "$root" Agent/dist agent-learning/app agent-learning/db agent-learning/pyproject.toml agent-learning/uv.lock deploy/ecs
echo "Backup ready: $backup"

# Preserve server .env, Compose ports and Nginx configuration.
tar -xzf "$archive" -C "$root" \
    Agent/dist agent-learning/app agent-learning/db \
    agent-learning/pyproject.toml agent-learning/uv.lock agent-learning/README.md \
    deploy/ecs/Dockerfile.api deploy/ecs/Dockerfile.api.dockerignore \
    deploy/ecs/Dockerfile.web deploy/ecs/Dockerfile.web.dockerignore

docker compose --progress plain build api web
docker compose run --rm --no-deps web nginx -t
docker compose up -d --no-deps --no-build --force-recreate --wait --wait-timeout 180 api web

ready=0
for attempt in $(seq 1 15); do
    if curl --noproxy '*' --max-time 5 -fsS http://127.0.0.1:8080/api/v1/health > "$backup/health.json"; then
        ready=1
        break
    fi
    sleep 2
done
test "$ready" -eq 1
curl --noproxy '*' --max-time 10 -fsS http://127.0.0.1:8080/ > "$backup/home.html"
grep -q 'index-cXoKjfWd.js' "$backup/home.html"
curl --noproxy '*' --max-time 10 -fsS http://127.0.0.1:8080/assets/index-cXoKjfWd.js -o /dev/null
docker compose ps
cat "$backup/health.json"
echo
echo 'Release verified: index-cXoKjfWd.js'
echo "Backup: $backup"
echo "Image rollback (does not restore the database):"
echo "docker compose -f compose.yaml -f $backup/rollback.yaml up -d --no-deps --no-build --force-recreate api web"
