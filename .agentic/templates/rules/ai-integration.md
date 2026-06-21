---
cache_key: template-rules-ai-integration-v1.0
type: template
---

# Rules template — AI integration (tech-agnostic)

Seed pro projektový `rules/ai-integration.md`. Watson kopíruje při setupu
(pokud projekt volá LLM/AI služby), Ted vlastní. Konkrétní SDK / model →
`stack/<target>.md`.

**Hranice:** tvar AI integrace (typované I/O, structured outputs, bezpečnost
promptu). Konkrétní knihovny (pydantic / zod / SDK) a model → `stack/`.

---

```markdown
# AI integration rules

Tech-agnostic vzor pro volání LLM/AI. Hygiena viz `.agentic/constitution.md`.
Konkrétní SDK a model viz `stack/<target>.md`.

## Typované I/O (povinné)
Každé volání LLM má **typovaná vstupní i výstupní schémata** — jasně dané
vstupy a výstupy (princip za pydantic / zod; nástroj v `stack/`). Výstup
modelu se parsuje a validuje proti schématu, nikdy se nekonzumuje jako
volný text.

## Structured outputs
Tam, kde to model/SDK umožní, vyžadovat schema-constrained výstup. Selhání
validace = typovaná chyba, ne tichý fallback.

## Prompty
Prompt je kód — verzovaný, oddělený od dat (šablona + parametry), ne
roztroušený hardcoded řetězec. Žádné secrets v promptu.

## Spolehlivost
- Background AI joby respektují idempotenci (constitution §Idempotence) a
  cancellability (constitution §Cancellability — stop flag mezi jednotkami).
- Ošetřit rate limits, timeouts, token limity; selhat typovaně, ne spadnout.
- Retry s rozumným backoff.

## Bezpečnost
- Uživatelský vstup do promptu = untrusted (prompt-injection awareness).
- Výstup z AI = untrusted: validovat před použitím (zvlášť než se stane
  vstupem do dalšího systému / DB / shellu). Pozor Heimdall.
```

---

## Pozn. pro Watson / Ted

- Tato oblast je relevantní jen pro projekty, které samy volají AI služby.
  Watson ji seeduje jen po detekci (fáze 2/4 interview — „voláte LLM?").
- Volba modelu a SDK je stack rozhodnutí (Tony) — sem nepatří konkrétní
  jména, jen princip typovaného a bezpečného I/O.
