---
wave: 2026-06-13-code-quality
from: implementace (autonomní noční běh, user delegoval rozhodnutí)
to: ranní review (Vitek)
type: close
returns_to: null
timestamp: 2026-06-13T03:00:00+02:00
---

# CLOSE: code-quality pass nad enginem (constitution §Standardy kódu)

User feedback: *„ty python scripty nejsou vubec pekne napsane … není to kód který bych chtěl
a zvládal číst … drž se mých pravidel … nechci aby to byl vibe coding."* Zadání: dotáhnout
engine k tvým standardům (`constitution.md §Standardy kódu`), zamyslet se nad bash vs python.

**Čistý refactor, nula změny chování** — brána zelená po KAŽDÉM commitu (11 commitů, modul po modulu).

## Rozhodnutí (delegoval jsi „je to na tobě")

- **(a) Bash shimy ZŮSTÁVAJÍ.** Jsou 1-řádkové (`exec python3 core/X.py "$@"`) a tvoří
  **agent-facing kontrakt** — `flow.md` + 10+ agentů + `ARCHITECTURE.md` volají `run.sh drive`,
  ne `python3 core/run.py`. „Vše v Pythonu" by znamenalo buď ošklivé call-sites, nebo přidat
  packaging/entry-point — víc mašinerie pro nástroj distribuovaný **kopírováním souborů**
  (`agentic-sync`). Shimy jsou paradoxně nejčistší část repa. Problém byl v Pythonu, ne v bashi.
- **(b) Komentáře/docstringy ČESKY** — vědomá výjimka z „kód anglicky". Engine je interní český
  nástroj (jako ústava/STATE/handoffy/agenti); ty češtinu čteš pohodlně, přepis do AJ = obří churn
  bez zisku. Identifikátory zůstaly anglicky, CLI hlášky česky (ústava má opt-out pro interní tools).
  Zdokumentováno v `core/README.md §Standardy kódu`.
- **(c) mypy do brány** — udržel jsem celé `core/` (16 souborů) mypy-clean a zapojil do CI
  (`pipeline-guardrails.yml`). Non-strict config (`scripts/pipeline/mypy.ini`) — stav běhu / YAML
  jsou genuinně dynamické, nehoníme každou hodnotu; jde o explicitní rozhraní.

## Co se změnilo (per modul, 11 commitů)

| modul | změna |
|---|---|
| predicate.py | typy + `EvalContext`/`Expr` Protocoly; `is_free` v `__init__` (mizí property override-clash) |
| vocab.py, runstate.py | typy; `coerce_awaiting_human` vnořený ternár → if blok |
| graph.py | typy + `ActivationContext` Protocol (role/agent status); `reachable` přijímá str\|None |
| common.py | typy + `mypy.ini`; `expand_type` ternár → if; `write_state` txt-not-None guard |
| frontier.py | typy; `frontier_for_state` vnořený bool-ternár → if; `compute` walrus; `compute_next` prázdný RunState místo None |
| result.py | `main()` ~175ř → 8 pojmenovaných kroků; DRY: inline zápis → `common.write_state` (byl bajt-identický duplikát) |
| run.py | `partition_ready`/`print_dispatch` extrakce; odstraněno mrtvé `passthru` + `dump_block` import |
| check.py | `main()` ~250ř → C1–C15 jako funkce vracející `list[str]`; opraven `e` reuse; **výstup BYTE-IDENTICKÝ** (real i broken graf) |
| status.py | typy; `awaiting` ternár → if |
| ledger/scaffold/compose/feature/lib/apply_feature | typy na main()+helpery; ledger nested ternár → if/elif/else; apply_feature re.match None-safe |

Commity: `0549113`→`532eecf` (`git log --oneline | grep code-quality`).

## Výsledek vs tvoje pravidla

- **Explicitní typy parametrů/návratů** (ř.330) — splněno napříč `core/`; mypy clean (16 souborů).
- **Jedna odpovědnost, ne dlouhá nudle** (ř.339) — `result.main`/`check.main`/`run.drive` rozloženy.
- **Čitelnost > kompaktnost, ne ternár pro řízení toku** (ř.348/351) — všechny vnořené ternáry/lambdy pryč.
- **Duck-type kontrakty jako Protocol** — engine se neprovazuje konkrétními třídami (sedí s „blind contracts").
- `eval()` = 0 (z dřívější vlny), dead code odstraněn.

## Brána (zelená finálně i po každém commitu)

```
selftest.sh                                   57/57  „VŠE PROŠLO"
check.sh                                       C1–C15 RESULT: OK  (+ byte-diff vs baseline = prázdný)
pytest scripts/pipeline/tests                  75/75
mypy --config-file scripts/pipeline/mypy.ini scripts/pipeline/core   16 souborů clean
accept-createdat.py                            exit 0
parity-predicate.py                            PARITY OK
```

## Otevřené / k tvému zvážení

- **CI nově instaluje mypy** (`pip install … mypy`) + krok. Pokud nechceš mypy v CI, smaž ten krok;
  type anotace zůstanou jako čitelnostní hodnota i bez něj.
- Komentáře česky = moje rozhodnutí; když chceš striktně AJ dle ústavy, řekni — udělám samostatnou vlnu.
- `frontier.Ctx` flag-resolution politika (touches_db→has_db, design_source→author, targets) je jediná
  netriviální logika bez izolovaného unit testu (drží ji selftest) — nabízený follow-up z minula.
