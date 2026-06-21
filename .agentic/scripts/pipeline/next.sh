#!/usr/bin/env bash
# next.sh — tenký shim na core/frontier.py (deterministický výpočet dalšího uzlu / frontieru).
exec python3 "$(dirname "${BASH_SOURCE[0]}")/core/frontier.py" "$@"
