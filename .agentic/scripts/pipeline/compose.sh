#!/usr/bin/env bash
# compose.sh — tenký shim na core/compose.py (founding APPLY engine: scaffold + features).
exec python3 "$(dirname "${BASH_SOURCE[0]}")/core/compose.py" "$@"
