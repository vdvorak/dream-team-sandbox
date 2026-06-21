---
cache_key: template-design-brief-v1.0
type: template
---

# Design Brief template

Denisa generuje tento brief v **intake módu** (když user dodá vlastní design).
Je to ready-to-paste prompt pro externí design nástroj (Claude design / v0 /
Figma AI), naplněný tak, aby výsledek **už ladil s design manuálem** projektu.

Denisa vyplní placeholdery z: `specs/<feature>.md`, `acceptance/<feature>.md`,
`design/manual/tokens.css`, `design/manual/README.md`. Uloží do
`design/<feature>/design-brief.md`.

---

```markdown
# Design Brief — <Feature>

> Vlož tento prompt do Claude design / v0 / Figma AI. Výstup vrať zpět —
> bude zaregistrován jako mockup a ověřen proti design manuálu.

## Co tvoříme
<2–3 věty z feature spec — co to dělá, pro koho>

## Obrazovky / pohledy
- <screen 1 — stručný popis obsahu>
- <screen 2>

## Stavy k pokrytí (každý zvlášť)
- **Loading**: <kdy, co se zobrazí>
- **Error**: <jaké chyby, jak komunikovat>
- **Empty**: <prázdný stav, call-to-action>
- **Success**: <po dokončení akce>

## Design systém — DODRŽ PŘESNĚ

**Barvy** (CSS custom properties — použij JEN tyto, žádné jiné hex):
<vlož skutečné tokeny z design/manual/tokens.css, např.:>
  --color-primary: #...
  --color-bg: #...
  --color-text: #...
  --color-error: #...

**Spacing scale** (použij JEN tyto):
  --space-1: 4px ... --space-10: ...

**Typografie**:
  font-family: <z manuálu>
  scale: <h1/h2/body/caption velikosti>

**Komponenty k reuse** (NEtvoř nové varianty — použij tyto z manuálu):
  - Button (varianty: <primary/secondary/...>)
  - FormField (label + input + error)
  - Card
  - <další relevantní>

**Voice/tone**: <z design/manual/README.md — např. "věcný, klidný, ne alarmistický">

## Accessibility (povinné)
- WCAG-AA kontrast (≥ 4.5:1 text)
- Viditelné focus states
- Touch targets ≥ 44×44px (mobilní)

## Výstupní formát
Vrať **HTML + CSS** jako jeden soubor. CSS používá výhradně výše uvedené
CSS custom properties (`--color-*`, `--space-*`). ŽÁDNÉ hardcoded hex barvy
ani px hodnoty mimo spacing scale. Žádný JavaScript / logika — jen vizuál.
```

---

## Pozn. pro Denisu

- Tokeny vkládej **skutečné** (čti `design/manual/tokens.css`), ne placeholder
  jména — aby externí nástroj produkoval design s reálnými hodnotami systému.
- Pokud manuál pro feature nemá potřebnou komponentu, **uveď to v briefu**
  („potřebuje nový pattern X — bude doplněn do manuálu") a eskaluj Leonard.
- Po návratu designu od usera: intake validace (tokeny, states, a11y) →
  `mockup.html`. Deviace od manuálu → Leonard.
