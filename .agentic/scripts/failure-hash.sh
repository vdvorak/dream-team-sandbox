#!/usr/bin/env bash
# failure-hash.sh — Vypočítá deterministický hash failure signature pro
# detekci "stejné chyby po N×" (Constitution §B2).
#
# Usage: scripts/failure-hash.sh <check> <error_type> <location>
#
# Příklad:
#   scripts/failure-hash.sh test_export_pdf TimeoutError services/export.py
#   → 8a4f2c1b
#
# Implementace: SHA-256 prvních 8 hex znaků (dostatečné pro counter v rámci
# jedné wave, ne global uniqueness).

set -euo pipefail

if [[ $# -ne 3 ]]; then
  echo "Usage: $0 <check> <error_type> <location>" >&2
  exit 1
fi

# Concat with delimiter, hash, take first 8 hex chars
echo -n "$1::$2::$3" | sha256sum | cut -c1-8
