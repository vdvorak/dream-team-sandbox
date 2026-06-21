---
cache_key: template-migration-plan-v1.0
type: template
---

# Migration plan template

Povinný formát pro každou změnu kontraktu, která je **breaking** (rozbije
existujícího klienta, ztratí data, změní stable API shape, smaže produkční
data, atd.). Bez plánu = BLOCKER per Constitution §Kritická pravidla.

Schvalovatel: **vždy člověk (L3)** pro destruktivní migrace.

```yaml
---
wave: <wave-id>
migration_id: <unique-id>     # např. 0042-drop-legacy-export-metadata
type: breaking-change
artifact: contract-api | contract-db | rules | stack
schvalovatel: human (L3)
timestamp: <ISO-8601>
---
```

# Migration plan: <stručný popis>

## 1. Co se mění

Konkrétní změna. Citace předtím/potom, pokud aplikovatelné.

**Před:**
```
<předchozí state — řádek z OpenAPI, schema, atd.>
```

**Po:**
```
<nový state>
```

## 2. Kdo se rozbije

Explicitní seznam toho, co změna naruší:

- **Klienti API**: <kteří endpointy, kteří klienti>
- **Existující data**: <jaká data, kolik řádků, kde>
- **Existující features**: <které části kódu se musí změnit>
- **Externí integrace**: <pokud relevantní>

Pokud nic se nerozbije ("additive change") — uveď to a doložit:
```
SELECT COUNT(*) FROM <table> WHERE <condition> = 0 (verified <date>)
```

## 3. Jak migrovat (krok za krokem)

Atomické kroky v pořadí:

1. <krok 1>
2. <krok 2>
3. ...

Pro DB migrace: konkrétní SQL nebo migration script reference.

Pro API breaking changes: deprecation window, koexistence starého a nového,
final cutover.

## 4. Rollback plán

Co dělat, pokud migrace selže nebo se objeví problém:

1. <rollback krok 1>
2. <rollback krok 2>

Konkrétní SQL/script, který obnoví předchozí stav. Pro nedektruktivní
migrace: trivial (drop new column). Pro destruktivní: explicitní výpis
proč rollback **není možný** + co je backup plan.

## 5. Deprecation timeline (pokud relevantní)

Pokud API breaking, ne destruktivní:

- **Datum oznámení deprecace**: <date>
- **Datum end-of-life**: <date>
- **Komunikační kanály**: <kde se klient dozví>
- **Migration guide pro klienty**: <link nebo inline>

Pokud destruktivní change bez deprecation window: explicitně uveď proč
není potřeba (typicky internal-only change, žádné externí klienty).

## 6. Production impact

- **Downtime**: NONE | <N minut>
- **Data loss risk**: NONE | <popis>
- **Performance impact during migration**: <popis>

## === SCHVÁLENÍ ===
```
Schvalovatel: human (L3)
Datum žádosti: <ISO-8601>
Odpověď: [ ] SCHVÁLENO  [ ] ODMÍTNUTO  [ ] OTÁZKA
Důvod / komentář:
```

Po schválení: zápis do `audit/destructive-ops.md` s timestamp,
schvalovatelem, výsledkem.
