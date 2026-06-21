#!/usr/bin/env bash
# intake-signals.sh — deterministické sub-signály pro intake klasifikaci (prior, ne verdikt).
#
# `class` (feature|bugfix|improvement) je úsudek LLM (porozumění textu) — ten TENHLE skript
# NEPOČÍTÁ. Odvozuje jen sub-signály, které úsudek NEjsou:
#   has_signature — existuje strukturovaný failure-signature dokument? (frontmatter `type: failure`
#                   v handoffs/<wave>/, nebo soubor *failure-signature*). ano/ne, ne „od oka".
#   tier prior    — z complexity-estimate.sh (files/loc/sensitive → XS/S/M/L); vstup do
#                   lightweight rozhodnutí. LLM ho potvrdí/přebije, nepočítá od nuly.
#
# Usage:
#   scripts/intake-signals.sh [--wave <wave-id>] [<změněný-soubor> ...]
#   (bez --wave: vezme nejnovější adresář v handoffs/; bez souborů: complexity z git diffu)
#
# Výstup (stdin-friendly, key=value): orchestrátor ho bere jako VSTUP do intake `done` envelope
# (has_signature flag) a model-routing prioru — neopisuje ručně. Exit 0 vždy (je to prior).
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

wave=""
files=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --wave) wave="$2"; shift 2 ;;
    *)      files+=("$1"); shift ;;
  esac
done

# ── has_signature: deterministická detekce failure-signature dokumentu ────────────
# Konvence: failure-signature handoff nese frontmatter `type: failure` (templates/failure-signature.md)
# nebo má v názvu *failure-signature*. Hledáme v dané (nebo nejnovější) wave složce handoffs/.
hs="false"; sig_src="-"
handoffs_dir="handoffs"
if [[ -d "$handoffs_dir" ]]; then
  if [[ -z "$wave" ]]; then
    wave="$(ls -t "$handoffs_dir" 2>/dev/null | head -1 || true)"
  fi
  wdir="$handoffs_dir/$wave"
  if [[ -n "$wave" && -d "$wdir" ]]; then
    # název *failure-signature*
    if compgen -G "$wdir/*failure-signature*" > /dev/null 2>&1; then
      hs="true"; sig_src="$(ls "$wdir"/*failure-signature* 2>/dev/null | head -1)"
    else
      # frontmatter type: failure (return packet)
      match="$(grep -lE '^type:\s*failure\b' "$wdir"/*.md 2>/dev/null | head -1 || true)"
      if [[ -n "$match" ]]; then hs="true"; sig_src="$match"; fi
    fi
  fi
fi

# ── tier prior: deleguj na complexity-estimate.sh (NEduplikuj jeho logiku) ─────────
# Předáme dané soubory; bez nich complexity-estimate vezme git diff sám.
cest="$(bash "$HERE/complexity-estimate.sh" "${files[@]:-}" 2>/dev/null || true)"
tier="$(printf '%s\n' "$cest" | sed -n 's/.*tier=\([A-Z]*\).*/\1/p' | head -1)"
[[ -z "$tier" ]] && tier="?"

echo "has_signature=$hs"
echo "signature_source=$sig_src"
echo "tier_prior=$tier"
echo "wave=${wave:--}"
echo "# prior, ne verdikt: class klasifikuj úsudkem; has_signature ber jako fakt;"
echo "# tier_prior potvrď/přebij dle flow.md §Model routing (sensitive nuance je úsudek)."
