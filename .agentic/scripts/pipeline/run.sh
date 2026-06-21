#!/usr/bin/env bash
# run.sh — tenký shim na core/run.py (logika tam). Jednotný vstup do runneru:
# start/active/skip/status/next/drive/done/resolve-loop/summary/check/scaffold.
#
# Commit-on-done je OPT-IN (nodecommit.commit_enabled() default OFF, viz incident 2026-06-20).
# Zapneme ho VÝHRADNĚ pro orchestrátorovu CLI vlnu = subcommandy `done`/`drive`. Ostatní
# subcommandy (status/next/check/repair/checkpoint/start/…) ho nezapínají — commitovat nemají.
# RESPEKTUJEME existující hodnotu (`${VAR:-1}`), aby šel manuální override na 0 (CI/hermetic).
# Serverové `/api/done` ani testy přes tenhle shim nejdou → flag zůstane unset → necommitují.
case "${1:-}" in
  done|drive) export AGENTIC_NODE_COMMIT="${AGENTIC_NODE_COMMIT:-1}" ;;
esac
exec python3 "$(dirname "${BASH_SOURCE[0]}")/core/run.py" "$@"
