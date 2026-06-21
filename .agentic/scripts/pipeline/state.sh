#!/usr/bin/env bash
# state.sh — tenký shim na core/status.py (strojový stav běhu z current-run.md).
exec python3 "$(dirname "${BASH_SOURCE[0]}")/core/status.py" "$@"
