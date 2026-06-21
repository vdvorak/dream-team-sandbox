#!/usr/bin/env bash
# self-host-init.sh — tenký shim na core/self_host_init.py (seed PRODUCT vrstvy pro self-host).
exec python3 "$(dirname "${BASH_SOURCE[0]}")/core/self_host_init.py" "$@"
