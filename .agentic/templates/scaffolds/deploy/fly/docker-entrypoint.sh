#!/bin/bash
set -eo pipefail

# Fly single-machine entrypoint: embedded PostgreSQL + migrations + server.
# PLATFORM pattern (stack-agnostic) except the last line (run command).

DATA_DIR=/data
PG_DATA="$DATA_DIR/postgres"
PG_BIN="/usr/lib/postgresql/16/bin"
PG_PORT=5432
APP_DB="${APP_DB:-app}"

# ── APP_SECRET_KEY auto-gen, persisted on the volume (survives restart) ──
SECRET_KEY_FILE="$DATA_DIR/app_secret_key"
if [ -z "${APP_SECRET_KEY:-}" ]; then
    if [ -f "$SECRET_KEY_FILE" ]; then
        export APP_SECRET_KEY="$(cat "$SECRET_KEY_FILE")"
    else
        mkdir -p "$DATA_DIR"
        export APP_SECRET_KEY="$(python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())')"
        echo "$APP_SECRET_KEY" > "$SECRET_KEY_FILE"
        chmod 600 "$SECRET_KEY_FILE"
    fi
fi

# ── PostgreSQL init (once, on the volume) ──
if [ ! -f "$PG_DATA/PG_VERSION" ]; then
    mkdir -p "$PG_DATA"; chown postgres:postgres "$PG_DATA"
    su -s /bin/bash postgres -c "$PG_BIN/initdb -D $PG_DATA --auth=trust --locale=C --encoding=UTF8"
fi
su -s /bin/bash postgres -c "$PG_BIN/pg_ctl start -D $PG_DATA -w -l $DATA_DIR/postgres/pg.log -o '-c listen_addresses=localhost -c port=$PG_PORT'"
su -s /bin/bash postgres -c "psql -p $PG_PORT -tc \"SELECT 1 FROM pg_roles WHERE rolname='$APP_DB'\" | grep -q 1" \
    || su -s /bin/bash postgres -c "psql -p $PG_PORT -c \"CREATE USER $APP_DB WITH PASSWORD '$APP_DB';\""
su -s /bin/bash postgres -c "psql -p $PG_PORT -tc \"SELECT 1 FROM pg_database WHERE datname='$APP_DB'\" | grep -q 1" \
    || su -s /bin/bash postgres -c "createdb -p $PG_PORT -O $APP_DB $APP_DB"

# ── Migrations (idempotent via schema_migrations; init/ then migrations/) ──
if [ "${AUTO_MIGRATE:-false}" = "true" ]; then
    su -s /bin/bash postgres -c "psql -p $PG_PORT -d $APP_DB -U $APP_DB -c \"CREATE TABLE IF NOT EXISTS schema_migrations (version VARCHAR(255) PRIMARY KEY, applied_at TIMESTAMPTZ DEFAULT NOW());\""
    for dir in /app/contracts/db/init /app/contracts/db/migrations; do
        [ -d "$dir" ] || continue
        for f in $(ls "$dir"/*.sql 2>/dev/null | sort -V); do
            [ -f "$f" ] || continue
            key="$(basename "$dir")/$(basename "$f")"
            applied=$(su -s /bin/bash postgres -c "psql -p $PG_PORT -d $APP_DB -U $APP_DB -tAc \"SELECT COUNT(*) FROM schema_migrations WHERE version='$key'\"")
            if [ "$applied" = "0" ]; then
                echo "[deploy] migration: $key"
                su -s /bin/bash postgres -c "psql -p $PG_PORT -d $APP_DB -U $APP_DB -f '$f'"
                su -s /bin/bash postgres -c "psql -p $PG_PORT -d $APP_DB -U $APP_DB -c \"INSERT INTO schema_migrations (version) VALUES ('$key');\""
            fi
        done
    done
fi

mkdir -p "${UPLOAD_DIR:-/tmp/app-uploads}"

# ── Pre-flight ──
[ -z "${DATABASE_URL:-}" ] && { echo "[deploy] ERROR: DATABASE_URL not set" >&2; exit 1; }
[ -z "${APP_SECRET_KEY:-}" ] && { echo "[deploy] ERROR: APP_SECRET_KEY not set" >&2; exit 1; }

# ── STACK-SPECIFIC: run command ──
cd /app/server
exec uvicorn src.main:app --host "${HOST:-0.0.0.0}" --port "${PORT:-8000}"
