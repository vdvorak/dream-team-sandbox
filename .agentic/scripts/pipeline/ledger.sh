#!/usr/bin/env bash
# ledger.sh — tenký shim na core/ledger.py (cost + čas běhu z runs/<run>/ledger.yaml).
exec python3 "$(dirname "${BASH_SOURCE[0]}")/core/ledger.py" "$@"
