# pipeline/core — engine (Python)

Logika pipeline runneru. Dřív žila jako Python uvězněný v bash-heredocích uvnitř
`scripts/pipeline/*.sh`; vytaženo sem do importovatelných modulů (konec duplikace,
unit-testovatelné, app-ready dle `PROJECT-CONSTITUTION.md §Vize a mise`).

## Architektura

```
scripts/pipeline/
  *.sh            ← tenké shimy (3 ř): exec python3 core/<modul>.py "$@"
                     = stabilní CLI rozhraní (flow.md / CLAUDE.md / agenti se nemění)
  core/
    common.py     ← sdílené jádro: find/load graph+artifacts, read/write current-run
                     stavový blok (atomicky), coerce_flag, RESULT/EDGE_OUTCOMES,
                     expand_type, find_agentic. JEDEN zdroj pravdy (dřív duplikováno).
    ── doménový model (OO refactor; engine iteruje nad objekty, ne nad dicty) ──
    predicate.py  ← `when` jako parsovaný AST typovaných atomů (keystone): Verdict +
                     atomy + And/Or/Not + parser; .classify/.structural_live/.problems.
                     Nahradil trojí regex+eval() duplikaci; eval() z enginu PRYČ.
    vocab.py      ← Vocabulary: obal vocabulary.yaml (flag_kind/enum_values/kategorie
                     + fallbacky severities/model_tiers); fail-closed, missing → SKIP.
    graph.py      ← Node(+podtřídy)/Edge/Graph.load (lenientní) + dotazy (forward_producers/
                     reachable/return_target_for_fault/…); Node.is_active/drive_category.
    runstate.py   ← RunState: mutabilní obal current-run stavu (st dict = úložiště →
                     serializace bajt-identická); completion/re-flow/frontier mutátory.
    ── konzumenti ──
    frontier.py   ← next.sh    : Frontier třída nad Graph/RunState (ready-rule + staleness)
    result.py     ← result.sh  : envelope validace + F3 auto-derive + outcome handlery (polymorfně)
    run.py        ← run.sh     : orchestrace; drive() partition dle node.drive_category
    check.py      ← check.sh   : integrita grafu C1–C16 nad Graph/Vocabulary/Predicate.problems
    structure_check.py ← structure-check.sh : PRODUCT-layer tvar projektu (S1–S4: sekce/cesty/
                     project_type layout/active_roles) — „má projekt správný tvar" (sourozenec check)
    self_host_init.py ← self-host-init.sh : seed PRODUCT vrstvy pro self-host (framework sám sobě);
                     odvodí active_roles z grafu, založí config/constitution/state/current-run/backlog;
                     inverze structure_check (vytvoří ↔ ověří). Mechanická část; vizi/targety doplní Watson.
    status.py     ← state.sh   : strojový stav běhu (node-id validace přes Graph.load)
    ledger.py     ← ledger.sh  : cost + čas agregace
    scaffold.py   ← scaffold.sh : resolve scaffoldu z manifestu
    feature.py    ← feature.sh  : resolver feature knihovny (P7)
    compose.py    ← compose.sh  : founding APPLY (volá apply_feature přímo)
    apply_feature.py ← apply-feature.sh : APPLY engine feature
    lib.py        ← lib.sh      : vetted knihovna pro schopnost + stack
```

## Princip

- **Shim = rozhraní, core = logika.** `run.sh drive`, `result.sh <env>` atd. fungují
  identicky; mění se jen kde logika leží. Žádný kód neimportuje `.sh`.
- **Sourozenecké importy.** Moduly běží přes `python3 core/<modul>.py`, takže
  `sys.path[0]` = `core/` → `import common` funguje. App vrstva přidá `core/` na path
  a importuje `frontier` / `result` přímo.
- **Závislost:** python3 + PyYAML (jako dřív heredocy). Bash shimy = zero-dep CLI povrch.

## Standardy kódu (constitution §Standardy kódu)

- **Type anotace všude** — explicitní typy parametrů/návratů (signatury, doménový model).
  Verifikuje `mypy` (`scripts/pipeline/mypy.ini`, non-strict: stav běhu / YAML jsou genuinně
  dynamické `dict[str, Any]`). Duck-typed kontext = `Protocol` (`EvalContext`/`ActivationContext`/
  `Expr`) — moduly se neprovazují konkrétními třídami.
- **Jedna odpovědnost** — žádné dlouhé `main()` nudle; každá kontrola/krok je pojmenovaná funkce
  (check.py C1–C16, result.py validace/derive/advance, run.py partition/dispatch).
- **Komentáře/docstringy ČESKY** — vědomá výjimka z pravidla „kód anglicky": engine je interní
  český nástroj (jako ústava/STATE/handoffy/agenti). Identifikátory zůstávají anglicky; CLI
  hlášky česky (ústava má opt-out pro interní tools).

## Distribuce

`agentic-sync.sh` rozesílá `scripts/pipeline/*.sh` **i** `core/*.py` do `.agentic/` projektů
(bez `core/` by shimy nefungovaly). Fresh projekty přes `create-project` dostanou `core/`
klonem (committed). CI (`pipeline-guardrails.yml`) běží `check.sh` + `selftest.sh` přes shimy.

## Testy

Dvě vrstvy:

- **Integrační:** `scripts/pipeline/selftest.sh` (bash) drží 60 E2E scénářů přes shimy = guard
  nad celým řetězem (shim → python) + `check.sh` C1–C16 + createdat reproducer + parity-predicate
  (AST == stará atom/classify/flag_live).
- **Unit:** `scripts/pipeline/tests/` (pytest, 101 testů) nad doménovým modelem + guardy — `predicate`
  (atomy/kombinace/FAIL-prefix/parser/problems), `graph` (factory/is_active/drive_category/dotazy),
  `runstate` (mutátory). Spuštění: `python3 -m pytest scripts/pipeline/tests`. **DEV-only:** leží
  mimo distribuční globy (`pipeline/*.sh`, `core/*.py`), takže se NErozesílá do `.agentic/` projektů.

Plus **mypy** (type guard, `python3 -m mypy --config-file scripts/pipeline/mypy.ini
scripts/pipeline/core`). Všechny tři běží v CI (`pipeline-guardrails.yml`).
