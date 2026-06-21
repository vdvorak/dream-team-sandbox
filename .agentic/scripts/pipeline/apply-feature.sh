#!/usr/bin/env bash
# apply-feature.sh — tenký shim na core/apply_feature.py (APPLY engine feature knihovny).
exec python3 "$(dirname "${BASH_SOURCE[0]}")/core/apply_feature.py" "$@"
