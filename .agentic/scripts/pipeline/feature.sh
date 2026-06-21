#!/usr/bin/env bash
# feature.sh — tenký shim na core/feature.py (resolver feature knihovny P7).
exec python3 "$(dirname "${BASH_SOURCE[0]}")/core/feature.py" "$@"
