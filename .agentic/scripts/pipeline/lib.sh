#!/usr/bin/env bash
# lib.sh — tenký shim na core/lib.py (vetted knihovna pro schopnost + stack).
exec python3 "$(dirname "${BASH_SOURCE[0]}")/core/lib.py" "$@"
