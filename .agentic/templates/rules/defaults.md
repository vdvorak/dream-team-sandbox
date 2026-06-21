---
cache_key: template-rules-defaults-v1.0
type: template
---

# Rules template — defaults (tech-agnostic)

Seed pro projektový `rules/defaults.md`. Watson kopíruje při setupu (každý
projekt), Vision/Ted vlastní. Vzor: murio + UnagyDev.

**Hranice:** opakovaná **orchestrátor/spec rozhodnutí** dělaná bez dotazu —
NE hygiena (`constitution.md`), NE architektura (`backend.md`/`frontend.md`),
NE tech nástroj (`stack/`). Každý default MÁ výjimkovou klauzuli.

---

```markdown
# Defaults

Tech-agnostic defaulty pro rozhodnutí opakující se napříč features. Pokud spec
neřekne jinak, orchestrátor i workery je používají **bez dotazu**. Každý default
má explicitní výjimku — kdy neplatí (jinak sklouzne v implicitní pravidlo a
ztratí se možnost obhájit odchylku).

## Targety ve scope
- Default aktivní targety pro novou feature: <doplň dle projektu, např. server, web>
- Ostatní targety (mobile/desktop): `—` dokud není explicitní rozhodnutí

## Content seeding
- Default: filesystem `content/<feature>/<locale>.<ext>`
- Výjimky (odůvodnit ve spec): runtime-editovatelný obsah → DB tabulka;
  externí zdroj → adapter + cache

## Locale fallback
- Default: graceful fallback na výchozí locale projektu
- Neplatí pro: validační chyby (explicitní error kód, ne fallback);
  audit / log eventy (locale-neutral)

## Přístup (auth)
- Default: nové endpointy auth-required
- Public = výjimka s odůvodněním ve spec + `security: []` v kontraktu

## Chybové chování
- Safety-critical obsah: graceful degradation (fallback obsah, ne error/prázdno)
- Neplatí pro: user input validaci (fail explicitně s kódem); security akce
  (fail bezpečně, ne graceful)

## Eskalace opakované ambiguity
- Stejná ambiguita ve 2+ features bez defaultu = BLOCKER pro spec-author —
  doplnit default sem PŘED pokračováním, ne improvizovat.
```

---

## Pozn. pro Watson / Vision

- Seeduje se každému projektu (orchestrátor potřebuje defaulty vždy). Hodnoty
  v `<...>` doplní Vision dle projektu při prvním feature.
- Pozor na hranici: pokud se „default" týká tvaru kódu, patří do `rules/backend`
  nebo `rules/frontend`, ne sem. Sem jen rozhodnutí typu „co se předpokládá".
