# Backlog: Flow gapy odhalené self-hostingem (dogfood)

**Třída:** improvement · **Stav:** VŠECH 5 vyřešeno (#1/#2/#4/#5 fix, #3 by-design) · **Priorita:** —

Nalezeno při prvním reálném self-hosted běhu (`handoffs/2026-06-13-p5-human-interaction/`).
**Všech 5 vyřešeno:** #1/#2/#4 opraveny v enginu/grafu (validováno — P5-like běh čistý bez workaroundů),
#5 formalizován (scope flagů), #3 vyjasněn jako správná hranice (ne gap). Issue lze zavřít.

## 1. project-config postrádá project-level flagy — ✅ FIXED
`active_targets`/`active_roles` nestačí — `backend` edge je gated `project.has_server`,
db-schema `project.has_db`. Bez flagů → edge UNKNOWN → uzel se nedispatchne. **Fix:** Watson/init
musí odvodit `has_server`/`has_db` z deklarovaných targets (web s backendem → has_server:true).
Dnes ručně doplněno do `project-config.md §Project flags`.

**Fix:** `frontier.load_project_config` odvozuje `has_server/has_db/has_deploy` z `active_targets`
(backend/db/deploy sub-klíče); explicitní `flags:` přebijí (setdefault). project-config slimnut.

## 2. Klient fan-out není gated `has_ui` (graf gap) — ✅ FIXED
Edge `architecture → [web,mobile,desktop]` (a `ui-system → [...]`) nemá `when`; `web` uzel je gated
jen `project.targets.web`. → **no-UI feature (has_ui:false) na projektu s web targetem spustí web.**
**Fix:** `web` uzel `when: project.targets.web && spec.has_ui` (analogicky mobile/desktop), nebo
gate edge na `has_ui`. Pak `run.sh skip web` nebude potřeba pro backend-only features.

## 3. (meta) Graf vs framework meta-práce — ✅ RESOLVED (by-design hranice)
Při běhu se to jevilo jako gap, ale po opravě #2 se rozpadl: P5 (edit engine registru + check.py)
**protekl grafem čistě** přes `architecture → backend → qa → audit`. **Engine JE produkt frameworku**
→ engine kód / registry / schémata patří do delivery grafu (standardní role). Skutečně off-graph
zůstává: **agent-authoring** (Eywa — meta-agent, záměrně mimo delivery) a **governance docs**
(constitution/flow — deliberate změny, ne issue-flow). To je **správná hranice, ne gap**: delivery
graf dodává PRODUKT (engine teď, app potom); meta/governance je mimo. Kdyby v budoucnu vznikla potřeba
flow i pro agent-authoring, je to samostatný design (viz `watson-self-host-mode`).

**Fix:** `web/mobile/desktop` uzly mají `when: project.targets.X && spec.has_ui` (delivery.yaml).
Backend-only feature na projektu s web targetem už nespustí web. `run.sh skip` netřeba.

## 4. `skip` na inflight uzel ho nevyřadí z `frontier` (engine bug) — ✅ FIXED
`run.sh skip <node>` přidá do `skipped`, ale **neodebere z `frontier`** (inflight). Když je uzel
už dispatchnutý (jako `web` po fan-outu), zůstane inflight → běh visí („INFLIGHT: čeká na web").
**Fix:** `run.py mutate_state("skip")` nově vyřadí uzel i z `frontier` (inflight).

## 5. Feature-vs-projekt flag tension — ✅ FIXED
`has_server/db/deploy/design_source/targets` = **project** scope (schopnost projektu); `has_ui/
touches_db/has_signature` = **feature** scope (co feature touchne). Routing = `project-schopnost &&
feature-použití` (web: `targets.web && has_ui`; db-schema: `has_db && touches_db`). **Fix:** scope
formalizován v `vocabulary.yaml` (každý flag má `scope: project|feature` + princip v hlavičce).
Po #1 (engine odvozuje project flagy) + #2 (klient gated has_ui) routing model už sedí — #5 byl
hlavně implicitní model, teď explicitní. (Feature-level override `has_deploy` = nepotřeba: framework
`has_deploy:false` projekt-wide; app deployuje vše. Kdyby přišel internal-feature-no-deploy case → follow-up.)

## Pozn.
Žádný z gapů P5 neblokoval natrvalo — workaroundy fungovaly, běh doběhl na `done`. Celá smyčka
„běh flow → najdi gapy → oprav gapy" proběhla: 5 nálezů, 4 reálné fixy (engine/graf/registr) + 1
vyjasnění hranice. Self-hosting se sám vylepšil.
