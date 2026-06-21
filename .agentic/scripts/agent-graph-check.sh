#!/usr/bin/env bash
# agent-graph-check.sh — Ověří integritu agent definic a jejich vazby na graf (Eywa tool).
#
# Kontroly (DETERMINISTICKÉ — skript NAJDE, Eywa/člověk ROZHODNE co s nálezem):
#   1) Každý agent soubor existuje fyzicky v agents/
#   2) Frontmatter má povinná pole (name, role, short, transformations, cache_key)
#   3) Žádné dvě agent definice nemají stejný short
#   4) Write-scope overlap (N3) — dvojice agentů s neprázdným průnikem write-scope
#      glob cest. `handoffs/**` (a další sdílené reporty) jsou allowlistované.
#      Reálný překryv = BLOCKER (exit != 0).
#   5) Agent↔persona obousměrně (N1) — každý `agent:` v delivery.yaml má persona
#      soubor v agents/; každá NE-meta persona má `agent:` výskyt v grafu. Drift = finding.
#   6) Cast drift (N6) — persona shorty v INDEX.md §Cast ⊇ `agent:` bindingy v grafu.
#      Chybějící řádek v katalogu = drift finding.
#   7) Tools ↔ write-scope (N7) — read-only agent (bez Write/Edit; množina READONLY
#      v setup-claude-code.sh) smí deklarovat write-scope nejvýš sdílený allowlist
#      (handoffs/**, STATE.md). Write cíl mimo allowlist = FAIL (def slibuje zápis,
#      který tool nedovolí). Chrání před driftem opraveným u N6 (Edna/Heimdall).
#
# Princip (constitution §Filozofie #7): detekce je deterministická, rozhodnutí je úsudek.
# Dřív byly kontroly 4+5 explicitně delegovány „na LLM/Eywa okem" — to je přesně to,
# co tenhle skript ruší. Eywa nad nálezem rozhoduje (sloučit / zúžit / povolit), nedetekuje.
#
# Usage: bash .agentic/scripts/agent-graph-check.sh
# Spouští se z root projektu (kde je .agentic/) nebo přímo z dream-team/.

set -euo pipefail

# ── Lokalizace zdrojů ────────────────────────────────────────────────────────
AGENTS_DIR=".agentic/agents"
PIPELINE_DIR=".agentic/pipeline"
ROOT_DIR=".agentic"
if [[ ! -d "$AGENTS_DIR" ]]; then
  AGENTS_DIR="agents"
  PIPELINE_DIR="pipeline"
  ROOT_DIR="."
  if [[ ! -d "$AGENTS_DIR" ]]; then
    echo "agents/ folder not found" >&2
    exit 2
  fi
fi
DELIVERY="$PIPELINE_DIR/delivery.yaml"
INDEX="$AGENTS_DIR/INDEX.md"

# Generátor wrapperů je autorita nad `tools` (Write/Edit) — řádek `READONLY = {…}`
# v něm určuje, kdo NEMÁ Write/Edit. N7 čte READONLY odtud, ne z (potenciálně
# zastaralých) .claude/agents/ wrapperů.
SETUP_SCRIPT="$ROOT_DIR/scripts/setup/setup-claude-code.sh"

# Meta-persony stojí mimo standardní flow → nemají uzel v grafu (legitimně).
META_PERSONAS=" eywa-meta watson-interviewer monk-ideation "

# Sdílené write-scope cesty, do kterých smí psát víc agentů (koordinovaně/append-only).
# handoffs/** je per-wave dokument každého agenta; STATE.md je sdílený stav.
SCOPE_ALLOWLIST=" handoffs/** STATE.md "

found=0          # frontmatter / duplicate findings (WARN/FAIL → exit 1)
blocker=0        # write-scope overlap (BLOCKER → exit 1, vlastní hláška)

# ── 1–3) Frontmatter + duplicitní short ──────────────────────────────────────
shorts=()
for f in "$AGENTS_DIR"/*.md; do
  base=$(basename "$f")
  if [[ "$base" == "INDEX.md" || "$base" == "OVERVIEW.md" || "$base" == "ARCHITECTURE.md" ]]; then continue; fi

  short=$(awk '/^short:/ { print $2; exit }' "$f")

  if [[ -z "$short" ]]; then
    echo "WARN: $f has no 'short:' in frontmatter"
    found=1
  fi

  for existing in "${shorts[@]-}"; do
    if [[ -n "$short" && "$existing" == "$short" ]]; then
      echo "FAIL: duplicate short '$short' in $f"
      found=1
    fi
  done
  [[ -n "$short" ]] && shorts+=("$short")

  for field in role transformations cache_key; do
    if ! grep -q "^${field}:" "$f"; then
      echo "WARN: $f missing frontmatter field '$field'"
      found=1
    fi
  done
done

echo "---"
echo "Agents checked: ${#shorts[@]}"
echo "Shorts: ${shorts[*]-}"

# ── Helper: vytáhni kanonický write-scope blok agenta ─────────────────────────
# Bere řádek '**Write scope**:' a jeho continuation řádky až po prázdný řádek /
# další odrážku/nadpis. Pravidla (deterministická):
#   - Cesty v `(...)` závorkách = VYLOUČENÍ / kontext (`kromě X`, `cesty per Y`,
#     `append…`) → emitují se jako `EXCL:<cesta>` (odečtou se z overlapu).
#   - Continuation řádek začínající negací (`Žádná`, `žádná`, `kromě`, `mimo`,
#     `nikdy`, `jinak read-only`) je SEZNAM ZÁKAZŮ, ne scope → cesty z něj jdou
#     také jako `EXCL:` (nikdy ne jako write cíl).
#   - Zbytek backtick-cest = write-scope globy.
extract_write_scope() {
  local file="$1"
  awk '
    BEGIN { in_block = 0; paren_open = 0 }
    function emit(line,   tmp, n, arr, k, inside) {
      tmp = line
      # 0) pokračujeme uvnitř víceřádkové závorky z minulého řádku → vše až
      #    po případnou zavírací ) je kontext (EXCL). Bez ) zůstává paren_open.
      if (paren_open) {
        if (match(tmp, /\)/) > 0) {
          inside = substr(tmp, 1, RSTART - 1)
          tmp = substr(tmp, RSTART + 1)
          paren_open = 0
        } else {
          inside = tmp
          tmp = ""
        }
        n = split(inside, arr, "`")
        for (k = 2; k <= n; k += 2) { if (arr[k] != "") print "EXCL:" arr[k] }
      }
      # 1) párované závorky na řádku → EXCL
      while (match(tmp, /\([^)]*\)/) > 0) {
        inside = substr(tmp, RSTART, RLENGTH)
        n = split(inside, arr, "`")
        for (k = 2; k <= n; k += 2) { if (arr[k] != "") print "EXCL:" arr[k] }
        tmp = substr(tmp, 1, RSTART - 1) substr(tmp, RSTART + RLENGTH)
      }
      # 1b) nepárová otevírací ( bez zavírací ) → zbytek řádku je kontext,
      #     a další řádek pokračuje v závorce (paren_open).
      if (match(tmp, /\(/) > 0) {
        inside = substr(tmp, RSTART + 1)
        n = split(inside, arr, "`")
        for (k = 2; k <= n; k += 2) { if (arr[k] != "") print "EXCL:" arr[k] }
        tmp = substr(tmp, 1, RSTART - 1)
        paren_open = 1
      }
      # 2) zbylé backtick-cesty mimo závorky → write scope
      n = split(tmp, arr, "`")
      for (k = 2; k <= n; k += 2) { if (arr[k] != "") print arr[k] }
    }
    function emit_excl_only(line,   n, arr, k) {
      n = split(line, arr, "`")
      for (k = 2; k <= n; k += 2) { if (arr[k] != "") print "EXCL:" arr[k] }
    }
    /\*\*Write scope\*\*/ && /:/ && !/konflikt/ {
      in_block = 1; paren_open = 0; emit($0); next
    }
    in_block == 1 {
      if ($0 ~ /^[[:space:]]*$/ || $0 ~ /^#/ || $0 ~ /^[[:space:]]*-[[:space:]]/ || $0 ~ /^\*\*/) {
        in_block = 0; paren_open = 0; next
      }
      # continuation řádek se zákazem → vše jde do EXCL.
      # Pokud jsme uvnitř otevřené závorky z minulého řádku, drží emit() (paren_open).
      if (!paren_open && $0 ~ /[Žž]ádná|[Žž]ádné|kromě|mimo|nikdy|jinak read-only|read-only/) {
        emit_excl_only($0)
      } else {
        emit($0)
      }
    }
  ' "$file" \
    | grep -vE '§' \
    | sort -u
}

# Normalizuj glob na porovnatelný prefix: usekni '**', '*' a koncové '/'.
glob_prefix() {
  local g="$1"
  g="${g%%\*\**}"   # vše po prvním '**' pryč
  g="${g%%\**}"     # vše po prvním '*' pryč
  g="${g%/}"        # koncové '/'
  printf '%s' "$g"
}

is_allowlisted() {
  local g="$1"
  case "$SCOPE_ALLOWLIST" in
    *" $g "*) return 0 ;;
    *) return 1 ;;
  esac
}

# Dva prefixy kolidují, pokud je jeden prefixem druhého (na hranici cesty).
prefix_overlap() {
  local a="$1" b="$2"
  [[ -z "$a" || -z "$b" ]] && return 1
  if [[ "$a" == "$b" ]]; then return 0; fi
  if [[ "$b" == "$a"/* ]]; then return 0; fi
  if [[ "$a" == "$b"/* ]]; then return 0; fi
  return 1
}

# ── 4) Write-scope overlap (N3) ──────────────────────────────────────────────
echo "---"
echo "[4] Write-scope overlap (N3):"
scope_files=()
scope_shorts=()
for f in "$AGENTS_DIR"/*.md; do
  base=$(basename "$f")
  if [[ "$base" == "INDEX.md" || "$base" == "OVERVIEW.md" || "$base" == "ARCHITECTURE.md" ]]; then continue; fi
  s=$(awk '/^short:/ { print $2; exit }' "$f")
  [[ -z "$s" ]] && continue
  scope_files+=("$f")
  scope_shorts+=("$s")
done

# Leží kolizní prefix CELÝ uvnitř některé vyloučené domény (`EXCL:`)?
# Pokrytí platí jen když vyloučení je roven nebo PŘEDKEM kolize (excl ⊇ prefix) —
# NE naopak: vyloučení `server/_generated/` NEpokrývá širší kolizi na `server`.
covered_by_exclusion() {
  local prefix="$1"; shift
  local ex
  for ex in "$@"; do
    [[ -z "$ex" ]] && continue
    local ep
    ep=$(glob_prefix "$ex")
    [[ -z "$ep" ]] && continue
    if [[ "$prefix" == "$ep" || "$prefix" == "$ep"/* ]]; then return 0; fi
  done
  return 1
}

overlap_hits=0
for ((i = 0; i < ${#scope_files[@]}; i++)); do
  for ((j = i + 1; j < ${#scope_files[@]}; j++)); do
    si="${scope_shorts[$i]}"
    sj="${scope_shorts[$j]}"
    # Watson je bootstrap-only (scaffold copy, pak předává) → vynech z overlap auditu;
    # jeho jednorázový dosah do server/clients je dokumentovaná setup výjimka.
    if [[ "$si" == "watson-interviewer" || "$sj" == "watson-interviewer" ]]; then continue; fi

    # Rozděl na write cíle (globs_*) a vyloučení (excl_*).
    globs_i=(); excl_i=()
    while IFS= read -r line; do
      [[ -z "$line" ]] && continue
      if [[ "$line" == EXCL:* ]]; then excl_i+=("${line#EXCL:}"); else globs_i+=("$line"); fi
    done < <(extract_write_scope "${scope_files[$i]}")
    globs_j=(); excl_j=()
    while IFS= read -r line; do
      [[ -z "$line" ]] && continue
      if [[ "$line" == EXCL:* ]]; then excl_j+=("${line#EXCL:}"); else globs_j+=("$line"); fi
    done < <(extract_write_scope "${scope_files[$j]}")

    for gi in "${globs_i[@]-}"; do
      [[ -z "$gi" ]] && continue
      is_allowlisted "$gi" && continue
      pi=$(glob_prefix "$gi")
      [[ -z "$pi" ]] && continue
      for gj in "${globs_j[@]-}"; do
        [[ -z "$gj" ]] && continue
        is_allowlisted "$gj" && continue
        pj=$(glob_prefix "$gj")
        [[ -z "$pj" ]] && continue
        if prefix_overlap "$pi" "$pj"; then
          # reálné jen pokud kolizní oblast NENÍ vyloučená u žádného z agentů
          if covered_by_exclusion "$pi" "${excl_i[@]-}" "${excl_j[@]-}"; then continue; fi
          if covered_by_exclusion "$pj" "${excl_i[@]-}" "${excl_j[@]-}"; then continue; fi
          echo "BLOCKER: write-scope overlap: $si (\`$gi\`) ∩ $sj (\`$gj\`)"
          overlap_hits=1
          blocker=1
        fi
      done
    done
  done
done
if (( overlap_hits == 0 )); then
  echo "  none — žádný překryv write-scope cest mimo allowlist/vyloučení"
fi

# ── 5) Agent↔persona obousměrně (N1) ─────────────────────────────────────────
echo "---"
echo "[5] Agent↔persona binding (N1):"
n1_hits=0
if [[ ! -f "$DELIVERY" ]]; then
  echo "  WARN: $DELIVERY nenalezen — N1/N6 kontrola přeskočena"
  found=1
else
  mapfile -t graph_agents < <(grep -oE '^[[:space:]]*agent:[[:space:]]*[A-Za-z0-9_-]+' "$DELIVERY" \
    | sed -E 's/.*agent:[[:space:]]*//' | sort -u)

  # 5a) každý agent: v grafu má persona soubor
  for ga in "${graph_agents[@]-}"; do
    [[ -z "$ga" ]] && continue
    if [[ ! -f "$AGENTS_DIR/$ga.md" ]]; then
      echo "  FINDING: agent '$ga' v delivery.yaml NEMÁ persona soubor $AGENTS_DIR/$ga.md"
      n1_hits=1
      found=1
    fi
  done

  # 5b) každá NE-meta persona má agent: výskyt v grafu
  graph_blob=" ${graph_agents[*]-} "
  for s in "${shorts[@]-}"; do
    [[ -z "$s" ]] && continue
    case "$META_PERSONAS" in *" $s "*) continue ;; esac
    case "$graph_blob" in
      *" $s "*) : ;;
      *)
        echo "  FINDING: ne-meta persona '$s' NEMÁ 'agent:' binding v delivery.yaml"
        n1_hits=1
        found=1
        ;;
    esac
  done
fi
if (( n1_hits == 0 )); then
  echo "  ok — agent: bindingy a persony konzistentní v obou směrech"
fi

# ── 6) Cast drift INDEX.md ⊇ graf (N6) ───────────────────────────────────────
echo "---"
echo "[6] Cast drift INDEX.md ⊇ graf (N6):"
n6_hits=0
if [[ -f "$DELIVERY" && -f "$INDEX" ]]; then
  for ga in "${graph_agents[@]-}"; do
    [[ -z "$ga" ]] && continue
    # Cast tabulka má personu jako `short` v backtickách v prvním sloupci.
    if ! grep -qE "\`$ga\`" "$INDEX"; then
      echo "  FINDING: agent '$ga' z grafu CHYBÍ v INDEX.md §Cast"
      n6_hits=1
      found=1
    fi
  done
else
  echo "  WARN: $INDEX nebo $DELIVERY chybí — N6 přeskočena"
  found=1
fi
if (( n6_hits == 0 )); then
  echo "  ok — INDEX.md §Cast pokrývá všechny grafové bindingy"
fi

# ── 7) Tools ↔ write-scope konzistence (N7) ──────────────────────────────────
# Pravidlo: read-only agent (bez Write/Edit toolu) smí mít write-scope nanejvýš
# sdílené allowlist cesty (handoffs/**, STATE.md) — svůj envelope/výstup. Deklaruje-li
# write-scope na cokoli jiného, je to drift: definice slibuje zápis, který tool nedovolí.
# Autorita nad „kdo je read-only" = množina READONLY v generátoru wrapperů (ne wrappery
# samy — ty stárnou). Vyloučené (EXCL:) cesty se nepočítají — to je kontext/orchestrátor.
echo "---"
echo "[7] Tools ↔ write-scope konzistence (N7):"
n7_hits=0
if [[ ! -f "$SETUP_SCRIPT" ]]; then
  echo "  WARN: $SETUP_SCRIPT nenalezen — N7 (read-only ↔ write-scope) přeskočena"
  found=1
else
  # Vytáhni množinu READONLY = {"a", "b", ...} z generátoru → mezerami oddělený blob.
  readonly_blob=" $(grep -E '^READONLY[[:space:]]*=' "$SETUP_SCRIPT" \
    | grep -oE '"[A-Za-z0-9_-]+"' | tr -d '"' | tr '\n' ' ')"
  if [[ "$readonly_blob" == " " ]]; then
    echo "  WARN: nepodařilo se naparsovat READONLY z $SETUP_SCRIPT — N7 přeskočena"
    found=1
  else
    for f in "$AGENTS_DIR"/*.md; do
      base=$(basename "$f")
      if [[ "$base" == "INDEX.md" || "$base" == "OVERVIEW.md" || "$base" == "ARCHITECTURE.md" ]]; then continue; fi
      s=$(awk '/^short:/ { print $2; exit }' "$f")
      [[ -z "$s" ]] && continue
      # jen read-only agenti
      case "$readonly_blob" in *" $s "*) : ;; *) continue ;; esac
      # write CÍLE (ne EXCL:) mimo allowlist = porušení
      while IFS= read -r line; do
        [[ -z "$line" ]] && continue
        [[ "$line" == EXCL:* ]] && continue
        if ! is_allowlisted "$line"; then
          echo "  FAIL: read-only agent '$s' deklaruje write-scope '$line' bez Write/Edit toolu"
          echo "        → buď zúžit scope na handoffs/**, nebo přidat $s do non-readonly (Write/Edit)."
          n7_hits=1
          found=1
        fi
      done < <(extract_write_scope "$f")
    done
  fi
fi
if (( n7_hits == 0 )); then
  echo "  ok — žádný read-only agent nedeklaruje write-scope mimo sdílený allowlist"
fi

# ── Verdikt ──────────────────────────────────────────────────────────────────
echo "---"
if (( blocker != 0 )); then
  echo "agent-graph: BLOCKER (write-scope overlap)"
  exit 1
elif (( found == 0 )); then
  echo "agent-graph: OK"
  exit 0
else
  echo "agent-graph: FINDINGS"
  exit 1
fi
