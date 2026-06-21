#!/usr/bin/env bash
# check.sh — tenký shim na core/check.py (integrita grafu C1–C16).
exec python3 "$(dirname "${BASH_SOURCE[0]}")/core/check.py" "$@"
