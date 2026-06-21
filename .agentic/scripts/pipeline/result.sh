#!/usr/bin/env bash
# result.sh — tenký shim na core/result.py (/done: validace envelope + posun stavu).
exec python3 "$(dirname "${BASH_SOURCE[0]}")/core/result.py" "$@"
