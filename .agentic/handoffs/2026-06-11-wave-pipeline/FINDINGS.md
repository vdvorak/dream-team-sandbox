# wave-pipeline — dogfood findings (per-issue flow naostro)

Dogfood: `POST /users` nad čerstvě foundnutým `dogfood/userflow/` (python-fastapi+auth/jwt).
Executor profil **B**: orchestrátor (main session) řídí `run.sh drive`; každý uzel = čerstvý
izolovaný subagent nakrmený rolí `agents/<short>.md`. Měříme **route-determinismus** + kde smyčka drhne.

Klasifikace nálezu: **(a)** runner/graf/kontrakt (chybí engine vrstva, jako resolve-vs-apply u foundingu)
vs **(b)** agent (drift v obsahu uzlu).

---

## Findings

### F1 — (a) stale status v delivery.yaml
`pipeline/delivery.yaml` hlavička (ř. 6–8): *„STATUS: F1 — ZATÍM HO NEČTE žádný runner … Runner (F3)
začne graf vykonávat až po samostatném rozhodnutí."* — ale `run.sh drive`/`next.sh` graf reálně čtou
a `selftest.sh` je honí. Doc lže o stavu vlastního artefaktu. Drobné, ale přesně typ driftu, co hledáme.

### F2 — (a) HLAVNÍ: runner nemá zdroj project/spec flagů → každá strukturální větev = vynucený DECIDE
Přesný analog foundingového resolve-vs-apply.
- `next.sh` čte `has_server/has_db/has_ui/has_deploy` **jen z `--flag`** CLI argu. Parsování
  `project-config.md` (ř. 68–82) tyhle flagy **vůbec nečte** — extrahuje jen `agents` a `active_targets`.
- `run.sh drive` (ř. 95–96) `--flag` ani `--class` **nikdy nepředává** → v drive smyčce jsou všechny
  strukturální flagy permanentně `None`.
- `has_ui` je deklarovaný jako Vision **output** + je v jeho GATE OUTPUT (`ui-component: YES|NO`),
  ale `done`/result.sh ukládá jen output **typy**, ne **hodnotu**; `current-run.md` nemá pole na flagy.
  Router hodnotu nikdy nepřečte.
- **Důsledek:** `vision→{tony,design-source}`, `ted→{chandler,bob}`, fan-out `edna`, `l2-review→alfred`
  všechny degradují na DECIDE. „Deterministický dispatch" není deterministický pro **žádné** strukturální
  větvení — vždy spadne na úsudek orchestrátora. Flagy se **resolvnou** (Vision spec, struktura projektu),
  ale nic je **neaplikuje** do strojového stavu, který router čte.
- **Fix směr (návrh):** (1) `done` ingestne deklarované flag-outputy (has_ui z Vision envelope) do
  `current-run.md`; (2) project-config parsing čte has_server/has_db/has_deploy (struktura projektu);
  (3) `drive` předá oboje do `next.sh`. Pak strukturální větve = deterministické, DECIDE zůstane
  jen pro reálný úsudek (return paths, klasifikace).

---

### F3 — (a) chybí deterministický most handoff→envelope (ruční překlad orchestrátorem)
Druhý resolve-vs-apply šev. Subagent vrací **GATE OUTPUT** schéma (`spec: WRITTEN`, `ui-component: NO`,
`returns-to: tony-feasibility`, `weak-spot: …`). `run.sh done` ale chce **jiné** schéma
(`outcome`, `outputs: [{type}]`, `cost{model,tokens}`, `time{started,ended}`). Mezi nimi **není
extraktor** — orchestrátor envelope skládá ručně z hlavy (mapuje outputy na typy, fabrikuje cost/time).
Divergence-prone: dva běhy/dva orchestrátoři → různé envelopy ze stejného handoffu. Navíc `ui-component: NO`
z handoffu se do strojového stavu **nepřenese** (viz F2) — envelope nese jen `type: has_ui`, ne hodnotu.

### F4 — (a) BLOKUJÍCÍ: smyčka done↔drive nezavírá; `done` nuluje `active_node`, který `drive` potřebuje
`result.sh:132` natvrdo `active_node = None`. Ale `drive` počítá další krok přes `next.sh --from <active_node>`
→ po každém `done` spadne (`DRIVE: current-run.md neudává active_node`). Loop `drive → dispatch → done → drive`
se **nezavře** bez ručního `run.sh active <uzel>` mezi tím — a to k čemu ho nastavit orchestrátor v tu chvíli
neví (další uzel teprve počítá `drive`). **`selftest.sh` to nikdy nechytil**: po `done` volá vždy
`next --from <explicitní uzel>` + `status`, `drive` v sekvenci po `done` netestuje → zelený selftest je
falešně uklidňující. Toto je tvrdý blocker: per-issue flow přes `drive` reálně neběží za první uzel.
**Fix směr:** `done` nechá `active_node` = právě dokončený uzel (drive z něj spočítá odchozí hrany),
nebo `drive` při `active_node == null` fallbackuje na `completed[-1]`.

### F5 — (a) `drive` neimplementuje `kind: fork` (paralelní odbočka) — míchá ji do DECIDE jako alternativu
Hrana `vision → design-source {kind: fork, when: spec.has_ui}` je **paralelní větev** (rozběhni navíc,
nenahrazuje mainline `vision → tony-feasibility`). `drive`/`next.sh` ji ale vrací jako rovnocenného DECIDE
kandidáta vedle `tony-feasibility` → orchestrátor by „vybíral" mezi gate a paralelní odbočkou, což je
sémanticky špatně. Fork (i fan-out už řešený) potřebuje vlastní direktivu, ne DECIDE.

---

## Route trace (běh 1)

| krok | active_node | direktiva (drive) | outcome | pozn. |
|---|---|---|---|---|
| 1 | intake | DECIDE → vision | class=feature | jediný kandidát; class unknown (drive nepředá --class) → judgment [F2] |
| 2 | vision | dispatch (profil B) | PASS | reálný subagent, spec(49ř)+acceptance(8 AC), `ui-component: NO`; handoff→envelope ruční [F3] |
| 3 | (po done) | **CRASH** | — | `active_node=null` → `drive` spadl [F4 blocker] |
| 3' | vision (patch) | DECIDE → {tony, design-source} | PASS | i bezpodmínečný gate degraduje na DECIDE [F2]; fork míchán do voleb [F5] |

---

## Verdikt

**Per-issue flow přes `run.sh drive` reálně NEBĚŽÍ end-to-end.** Diagnóza jednoznačná a stejného tvaru
jako u foundingu: root cause = **(a) chybějící/neintegrovaná engine vrstva, ne (b) agent**. Vision (jediný
reálně dispatchnutý uzel) odvedl práci čistě. Dílčí scripty (`next`/`result`/`state`) procházejí `selftest`,
ale **v izolaci s explicitními argy** — uzavřená `drive` smyčka s flag-závislým routingem testovaná nikdy
nebyla, takže integrační mezery zůstaly neviditelné.

Nálezy seřazené dle závažnosti:
1. **F4 (blocker)** — `done` nuluje `active_node` → `drive` smyčka nezavírá. Bez tohohle flow neexistuje.
2. **F2 (major)** — runner nemá zdroj project/spec flagů → každá strukturální větev = vynucený DECIDE
   (resolve-vs-apply: flag se resolvne, neaplikuje do stavu).
3. **F5 (major)** — `kind: fork` neimplementován; paralelní odbočka míchána do DECIDE.
4. **F3 (major)** — žádný deterministický most handoff→envelope; ruční překlad = divergence-prone.
5. **F1 (minor)** — stale status v `delivery.yaml` hlavičce.

**Pozitivní:** envelope type-validace (C8/C9), ledger zápis, `start`/`active`/`done` mutace a profil-B
dispatch fungují. Kostra je tam; chybí **integrace smyčky** + **flag/handoff APPLY vrstva**.

---

## Fixes applied (pipeline-loop-fix — tatáž session)

Cíl: flow jede deterministicky end-to-end. Zaceleno přímo (engine/graf je meta-kód frameworku,
deterministický, jištěný selftestem — [[scripts-not-llm-enforcement]]).

- **F4 (loop-closure)** — `result.sh`: `done` nechá `active_node = dokončený uzel` (frontier pro `drive`),
  ne `null`; navíc `pending -= node`. Smyčka `done→drive` se zavírá.
- **F2 (flag source)** — APPLY vrstva flagů: `next.sh` čte `flags:` blok z `project-config.md`
  (has_server/has_db/has_deploy); `result.sh` ingestne `flags:` z envelope do `current-run.md`
  (has_ui z Vision); `run.sh drive` předá current-run flagy do `next.sh`. `current-run.md` má pole `flags`.
  Strukturální větve se rozhodují deterministicky.
- **F6 (NOVÝ, z verifikace)** — `ted→bob` osazeno `when: "has_server && !has_db"` → s DB jde bob přes
  chandlera (migrations), ne paralelně. `ted→chandler→bob` sekvenčně.
- **F7** — `dev→joey` hrany: prózní „unit tests green" → `when: PASS` (deterministický DISPATCH).
- **F8** — auditorské return hrany osazeny `when: FAIL` (return jen na finding; na PASS → join).
- **F9 (NOVÝ, z verifikace)** — `run.sh drive`: **fan-out barrier** (neadvancuj k join, dokud `pending != []`)
  + **join pass-through** (join neprodukuje práci → auto-advance). `audit-join→l2-review` bezpodmínečné.
- **F1** — `delivery.yaml` hlavička opravena (F3 status, runner graf vykonává).
- **Regression guard** — `selftest.sh` nově honí **celou `drive` smyčku** (fresh → human-gate l2-review),
  což přesně chybělo a maskovalo F4/F9. selftest **11/11**.

**Důkaz (live, `dogfood/userflow`, POST /users, has_ui=false):** `drive` protáhl
`intake →(DECIDE)→ vision → tony → ted → chandler → bob → joey →(fan-out)→ optimus/sheldon/heimdall/vitek
→(join)→ audit-join → HUMAN-GATE l2-review`. **Jediný DECIDE = intake klasifikace** (legitimní úsudek);
zbytek deterministický DISPATCH. Zastavení na L2 human-gate = správné (design).

**Zbývá (další wave, ne-blocker):** human-gate **continuation** (jak po L2/L3 vstupu pokračovat —
dnes `drive` u human-gate zastaví, není mechanismus „člověk OK → advance"); T3-post release path
(alfred/deploy/monitor) dogfoodem neprotažen; re-run s reálnými agenty (profil B) na zviditelnění (b).
