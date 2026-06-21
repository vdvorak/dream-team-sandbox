#!/usr/bin/env bash
# structure-check.sh — tenký shim na core/structure_check.py (PRODUCT-layer tvar projektu, S1–S4).
exec python3 "$(dirname "${BASH_SOURCE[0]}")/core/structure_check.py" "$@"
