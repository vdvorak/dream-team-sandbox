#!/usr/bin/env bash
# openapi-slice.sh — Extrahuje konkrétní operationId(s) z OpenAPI souboru.
#
# Místo načítání celého OpenAPI (často 100+ KB) si agent vyžádá jen
# konkrétní endpoint pro context (per Constitution §Scripted extraction first).
#
# Usage: scripts/openapi-slice.sh <operationId> [<operationId> ...]
#
# Hledá v `contracts/api/openapi.yaml` (nebo `.agentic/contracts/api/openapi.yaml`).
#
# Příklad:
#   scripts/openapi-slice.sh manuscriptExport
#
# Vyžaduje: yq (https://github.com/mikefarah/yq) nebo Python s ruamel/PyYAML.

set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <operationId> [<operationId> ...]" >&2
  exit 1
fi

# Locate OpenAPI file
for path in contracts/api/openapi.yaml .agentic/contracts/api/openapi.yaml \
            contracts/api/openapi.yml .agentic/contracts/api/openapi.yml; do
  if [[ -f "$path" ]]; then
    openapi="$path"
    break
  fi
done

if [[ -z "${openapi:-}" ]]; then
  echo "openapi.yaml not found in contracts/api/ or .agentic/contracts/api/" >&2
  exit 2
fi

# Use yq if available
if command -v yq >/dev/null 2>&1; then
  for op in "$@"; do
    yq eval "
      .paths | to_entries | map(
        .value | to_entries | map(
          select(.value.operationId == \"$op\")
        ) | .[0]
      ) | map(select(. != null)) | .[0]
    " "$openapi" 2>/dev/null || echo "operationId '$op' not found"
  done
  exit 0
fi

# Fallback: Python
if command -v python3 >/dev/null 2>&1; then
  python3 - "$openapi" "$@" <<'PYEOF'
import sys, yaml
openapi_path = sys.argv[1]
ops = sys.argv[2:]
with open(openapi_path) as f:
    data = yaml.safe_load(f)
for op_id in ops:
    found = False
    for path, methods in data.get("paths", {}).items():
        for method, op in methods.items():
            if isinstance(op, dict) and op.get("operationId") == op_id:
                print(f"--- {method.upper()} {path} (operationId: {op_id}) ---")
                print(yaml.dump(op, allow_unicode=True, sort_keys=False))
                found = True
                break
        if found:
            break
    if not found:
        print(f"operationId '{op_id}' not found", file=sys.stderr)
PYEOF
  exit 0
fi

echo "Neither yq nor python3 available — install one" >&2
exit 3
