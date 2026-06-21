#!/usr/bin/env bash
# Dev runner: starts a Postgres container and the Quarkus dev server.
set -euo pipefail

DB_CONTAINER="app-db"
DB_IMAGE="postgres:16"
DB_PORT="5433"

if ! docker info >/dev/null 2>&1; then
  echo "Docker is not running — starting..."; sudo systemctl start docker
fi

if ! docker ps --format '{{.Names}}' | grep -q "^${DB_CONTAINER}$"; then
  echo "Starting Postgres container ${DB_CONTAINER}..."
  docker run -d --name "${DB_CONTAINER}" \
    -e POSTGRES_USER=app -e POSTGRES_PASSWORD=app -e POSTGRES_DB=app \
    -p "${DB_PORT}:5432" "${DB_IMAGE}" >/dev/null || docker start "${DB_CONTAINER}"
fi

until docker exec "${DB_CONTAINER}" pg_isready -U app >/dev/null 2>&1; do
  echo "Waiting for Postgres..."; sleep 1
done

pkill -f quarkusDev || true
exec ./gradlew quarkusDev
