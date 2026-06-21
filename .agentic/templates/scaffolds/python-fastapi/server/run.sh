#!/usr/bin/env bash
# Dev runner: uvicorn with reload. Requires .env with DATABASE_URL (Postgres).
set -euo pipefail
exec uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
