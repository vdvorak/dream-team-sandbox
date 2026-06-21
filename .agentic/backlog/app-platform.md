# Backlog: Node-editor platforma (samostatný projekt)

**Třída:** feature (epická) · **Stav:** future · **Priorita:** north-star (po vyladění enginu)

## Co
Aplikace pro tvorbu agentních flow, konzumující tenhle engine. „Stejný engine, dvě UI" —
app renderuje a řídí to, co engine zapisuje do souborů. **Samostatný projekt** (python +
solidjs), ne součást tohoto repa.

## Proč
Zbavit se terminálu; vidět živě co flow dělá; nechat lidskou interakci proběhnout v UI;
otevřít tvorbu vlastních flow i mimo CLI. Determinismus zůstává — app je jen jiné UI nad
stejným souborovým enginem.

## Scope (hrubě)
- **Node editor** — agenti jako uzly; spojí se jen kompatibilní I/O (typované porty z `artifacts.yaml`).
- **AI-callable issue systém à la Jira** — board issues přes API, callable agenty.
- **AI-callable todos** — token-gated `/done` přechody (výstupy → vstupy dalšího uzlu); vzor `vtodo`
  (scoped token, optimistic concurrency přes verzi/If-Match).
- **Live view** — `current-run.md` → co flow zrovna dělá.
- **In-app human-interakce** — human-gate uzel + interaction registry (viz `human-interaction-registry`).

## Předpoklady (z enginu)
Typované I/O ✓, node-result `/done` obálka ✓, run ledger ✓, human-gate uzly ✓. Chybí: interaction
registry (P5), přesný token/concurrency kontrakt (sladit s vtodo).

## Most: souborový artefakt → app reprezentace
„Stejný engine, dvě UI." Co dnes engine zapisuje do souborů, to app jen renderuje a řídí —
crosswalk, co číst v enginu při stavbě každého kusu appky:

| Souborový artefakt (engine teď) | App reprezentace (potom) |
|---|---|
| `pipeline/delivery.yaml` (graf, typované I/O) | node editor (spojí jen kompatibilní I/O) |
| `current-run.md` (stav běhu) | live view — co flow zrovna dělá |
| node-result obálka + handoff (`result.sh`) | `/done` event: výstupy → vstupy dalšího kroku |
| `human-gate` uzel + `interactions.yaml` | in-app interakce přes typed interface (ne terminál) |
| `project-config` + issues v souborech | projektový board + issues přes API |
| (token model `vtodo`) | token-gated přístup — každý actor sahá jen na své |

## Pozn.
Engine MUSÍ zůstat app-ready (vše v souborech, typované I/O, strukturované přechody) — to je
akceptační kritérium každé engine změny, ne až starost appky.
