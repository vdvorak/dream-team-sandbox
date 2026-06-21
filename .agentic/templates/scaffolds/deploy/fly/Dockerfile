# Fly single-machine image: (web build →) server + embedded PostgreSQL.
# PLATFORM scaffold. Sekce STACK-SPECIFIC se mění dle stacku; zbytek je stejný.

# ── STACK-SPECIFIC: build web client (vynech, pokud projekt nemá web) ──
FROM node:20-slim AS web-builder
WORKDIR /app/clients/web
COPY clients/web/package*.json ./
RUN npm ci
COPY clients/web/ .
RUN npm run build

# ── STACK-SPECIFIC: server runtime base ──
FROM python:3.12-slim
WORKDIR /app

# ── PLATFORM: embedded PostgreSQL 16 (stack-agnostic) ──
RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc curl gnupg lsb-release && \
    curl -fsSL https://www.postgresql.org/media/keys/ACCC4CF8.asc \
        | gpg --dearmor -o /usr/share/keyrings/postgresql.gpg && \
    echo "deb [signed-by=/usr/share/keyrings/postgresql.gpg] https://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" \
        > /etc/apt/sources.list.d/pgdg.list && \
    apt-get update && apt-get install -y --no-install-recommends postgresql-16 && \
    pg_dropcluster --stop 16 main 2>/dev/null || true && \
    rm -rf /var/lib/apt/lists/*

# ── STACK-SPECIFIC: server deps + kód ──
COPY server/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY server/ ./server/
COPY contracts/ ./contracts/
COPY --from=web-builder /app/clients/web/dist ./clients/web/dist

ENV PYTHONUNBUFFERED=1
ENV APP_STATIC_DIR=/app/clients/web/dist
EXPOSE 8000

# ── PLATFORM: entrypoint (embedded pg + migrace + run) ──
COPY deploy/fly/docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh
ENTRYPOINT ["docker-entrypoint.sh"]
