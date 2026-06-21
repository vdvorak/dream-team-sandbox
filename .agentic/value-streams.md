---
cache_key: value-streams-v1.0
type: design
last_updated: 2026-05-30
status: FORWARD-LOOKING — pouze delivery stream je implementovaný
---

# Value-streams — návrh (design only)

> ⚠️ **Design, ne aktivní mechanika.** Dnes existuje **jeden** value-stream:
> *delivery* (software, `flow.md` + `agents/`). Tento dokument navrhuje, jak
> framework rozšířit o další proudy (např. marketing), aby se nový proud
> **nebolil na delivery pipeline**. Marketing agenti se nestaví, dokud nebudou
> aktuální — tady je jen architektura.

## Problém

Framework je dnes **jednorourový**: `T1 Idea→Spec → T2 Spec→Code → T3 Ověření`.
To je *software delivery*. Jiné výstupy (marketing obsah, kampaně, výzkum) mají
**jiný životní cyklus** — „Spec→Code" na landing page copy nesedí. Bolt nového
agenta (marketing) na delivery pipeline = špatný šev.

## Koncept

**Value-stream = jedna dráha produkující jeden typ výstupu**, s vlastním
mini-flow (vlastní transformace + role), ale sdílející univerzální substrát.

```
                    ┌─ delivery stream  (kód)      T1→T2→T3   [aktivní]
request → router ───┼─ marketing stream (obsah)    M1→M2→M3   [sketch]
                    └─ <další>                                  [budoucí]
```

## Co se sdílí vs co je per-stream

| Sdílené (univerzální substrát) | Per-stream |
|---|---|
| `constitution.md` axiomy (po refactoru — viz níže) | role / agenti proudu |
| Gates L0–L3 + schvalovací mechanika | transformace (T1/T2/T3 vs M1/M2/M3) |
| Per-agent **write-scope** disciplína | dispatch graf uvnitř proudu |
| Handoff formát (`templates/handoff.md`) | výstupní artefakty |
| `STATE.md`, `handoffs/`, wave model | |

**Specialisté mohou být cross-stream:** design (Denisa/Leonard) i security
(Heimdall) slouží delivery i marketingu; jen *core* role jsou per-stream.

## Routing

Orchestrátor klasifikuje request → vybere proud (dnes vždy delivery). Stream je
registrovaný v `project-config.md §streams` (default: `[delivery]`). Projekt
s marketingem: `streams: [delivery, marketing]`. Cross-stream handoff jde přes
stejný handoff formát (např. delivery „feature hotová" → marketing „ohlásit launch").

## Sketch: marketing stream (NEstaví se)

| Fáze | Analogie | Role (návrh) | Výstup |
|---|---|---|---|
| **M1** Idea→Brief | T1 | Content Strategist (PO-ekvivalent) | content brief (audience, cíl, message, kanál) |
| **M2** Brief→Asset | T2 | Copywriter + (cross-stream Denisa/Leonard pro vizuál) | copy / asset / email sekvence |
| **M3** Asset→Ověření | T3 | Brand/Voice + SEO + Claims auditor | konzistence, SEO, faktická kontrola |

## Kritický nález — constitution míchá universal + delivery-specific

Druhý proud odhalí, že část „univerzálních" pravidel je ve skutečnosti
**delivery-specific**:
- „Spec je source of truth, kód je artefakt" — delivery, ne marketing
- „Testy z spec" / „Cancellability" / „Idempotence" — delivery
- „Žádné emoji v kódu" — **marketing copy emoji běžně používá**

→ Až přijde druhý proud, je potřeba **rozdělit `constitution.md`** na:
- *axiomy* (opravdu universal: gates, write-scope, spec-nejasnost=STOP,
  destruktivní=souhlas, žádné placeholdery, bounded context, …)
- *delivery-stream pravidla* (přesunout do `flow.md` nebo `streams/delivery.md`)

Tohle je **předpoklad** pro marketing stream, ne dnešní úkol. Zaznamenáno, aby
se nezapomnělo.

## Invarianty

- Žádný proud neobchází constitution axiomy, gates ani write-scope.
- Každý proud má vlastní `agents/` podmnožinu + dispatch; nemíchá role napříč.
- Nový proud = nový `streams/<name>.md` (mini-flow) + jeho agenti; aktivace přes
  `project-config.md §streams`.

## Status

- **delivery** — jediný implementovaný proud (current `flow.md` + cast).
- **marketing** — sketch výše; staví se až bude aktuální (Eywa: nové role L3).
- constitution split — předpoklad, otevřený až s druhým proudem.

## Související design

- `pipeline-architecture.md` — návrh, jak *uvnitř* jednoho proudu převést flow
  na deklarativní stavový graf (uzly = agenti, hrany = handoffy). Ortogonální:
  value-streams řeší *kolik* proudů, pipeline-architecture *jak* jeden proud běží
  jako graf. Jeden stream = jeden graf.
