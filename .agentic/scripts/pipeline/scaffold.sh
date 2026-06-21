#!/usr/bin/env bash
# scaffold.sh — tenký shim na core/scaffold.py (resolve scaffoldu z manifestu).
exec python3 "$(dirname "${BASH_SOURCE[0]}")/core/scaffold.py" "$@"
