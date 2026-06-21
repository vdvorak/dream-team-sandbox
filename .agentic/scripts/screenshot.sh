#!/usr/bin/env bash
# screenshot.sh — Pořídí screenshot běžící app pro vizuální audit (Edna tool).
#
# Usage: scripts/screenshot.sh <url> [output.png] [viewport]
#
# Příklad:
#   scripts/screenshot.sh http://localhost:5173/settings .agentic/audit/settings.png
#   scripts/screenshot.sh http://localhost:5173/settings out.png 390x844   # mobile viewport
#
# Detekuje dostupný screenshot nástroj (chromium/chrome headless, nebo
# playwright pokud je v projektu). Edna pak screenshot přečte (vision) a
# porovná s design/<feature>/mockup.html.
#
# Pozn.: tool-agnostic best-effort. Pokud žádný nástroj není, vrátí exit 3
# a Edna eskaluje Alfred (CI má headless browser).

set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <url> [output.png] [viewport WxH]" >&2
  exit 1
fi

URL="$1"
OUT="${2:-.agentic/audit/screenshot.png}"
VIEWPORT="${3:-1280x800}"
W="${VIEWPORT%x*}"
H="${VIEWPORT#*x}"

mkdir -p "$(dirname "$OUT")"

# Try chromium/chrome headless
for bin in chromium chromium-browser google-chrome google-chrome-stable; do
  if command -v "$bin" >/dev/null 2>&1; then
    "$bin" --headless --disable-gpu --no-sandbox \
      --window-size="${W},${H}" \
      --screenshot="$OUT" "$URL" 2>/dev/null
    echo "✓ Screenshot: $OUT (via $bin, viewport ${VIEWPORT})"
    exit 0
  fi
done

# Try playwright (pokud projekt má node + playwright)
if command -v npx >/dev/null 2>&1 && [[ -f package.json ]] && grep -q playwright package.json 2>/dev/null; then
  npx playwright screenshot --viewport-size="${W},${H}" "$URL" "$OUT" 2>/dev/null && {
    echo "✓ Screenshot: $OUT (via playwright)"
    exit 0
  }
fi

echo "Žádný screenshot nástroj nenalezen (chromium/chrome/playwright)." >&2
echo "Edna: eskaluj Alfred — CI prostředí má headless browser pro vizuální audit." >&2
exit 3
