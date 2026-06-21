# Backlog: Human-interaction registry (P5)

**Třída:** feature · **Stav:** future (engine část P5 hotová; UI typologie pro app zbývá) · **Priorita:** předpoklad pro app

## Co
Typované interakční body — aby do běhu šlo **vstoupit** (agenti můžou potřebovat vstup od uživatele),
a app je uměla vyrenderovat deterministicky. **Vstup NIKDY přes terminál** — vždy **specializovaný
interface podle typu interakce**. Dnes `human-gate` uzel ví, že čeká na člověka (`interactions.yaml`:
blocking/level/kind), ale typy interakcí nejsou plně vymezené pro UI.

Vlajkový příklad (rozhoduje se o designu) — má už oporu ve flow (`design_source` flag / `design-intake`
role: `author|intake|derive`):
- **upload vlastního návrhu** (HTML soubor) → typed artefakt vstoupí do flow jako `mockup`, NEBO
- **spustit Denisu** → udělá návrh.

Oba jsou jiný typ interakce a app musí oba vyrenderovat jako jiný specializovaný UI (upload widget vs. „spustit agenta").

## Proč
Bez deterministicky definovaných interakcí by app musela improvizovat UI per-gate. Každý typ
interakce (choice / approval / ack / **upload** / text / delegate-vs-provide / …) má jasný vstup →
jasný výstup → typovaný artefakt do flow = minimální diverzita.

## Escape hatch (pozdějc)
Vstup do **live session agenta** pro případy nouze (když specializovaný interface nestačí). Záměrně
poslední možnost — porušuje determinismus, proto jen emergency. Řešit až po typovaných interakcích.

## Scope (hrubě)
- Rozšířit `pipeline/interactions.yaml` o úplnou typologii interakcí + jejich I/O schéma.
- Navázat na typované I/O (`artifacts.yaml`) — interakce produkuje typovaný výstup do flow.
- App pak renderuje interakci z jejího typu (žádný per-gate custom kód).

## Reference
`PROJECT-CONSTITUTION §Vize a mise` (human-interaction registry) · `pipeline/interactions.yaml` · `backlog/app-platform`.
