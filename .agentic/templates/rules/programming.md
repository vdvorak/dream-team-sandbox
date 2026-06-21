---
cache_key: template-rules-programming-v1.0
type: template
---

# Rules template — programming standards (tech-agnostic)

Seed pro projektový `rules/programming.md`. Watson ho kopíruje při setupu
(každý projekt), Ted vlastní. Platí pro všechny targety.

**Hranice:** obecné standardy kódu platné napříč projektem. NE universal hygiena
obsažená přímo v `constitution.md` (ta platí automaticky). NE tech-specifické
idiomy — ty do `stack/<target>.md`.

**Pozn.:** Universal verze tohoto souboru je v `.agentic/rules/programming.md`.
Projektový `rules/programming.md` přidá pouze odchylky nebo projekt-specifická
rozšíření. Pokud není co přidat, odkazuj na `.agentic/rules/programming.md`
bez duplikování.

---

```markdown
# Programming standards

Viz `.agentic/rules/programming.md` pro universal standardy.
Níže jsou projektové odchylky a rozšíření (pokud existují).

## Projektové odchylky

<!-- Ted nebo Bob doplní zde. Pokud žádné nejsou, tento soubor může
     zůstat jako pouhý odkaz na universal rules. -->
```

---

## Pozn. pro Watson / Ted

- Tento soubor je záměrně minimální — universal verze je v `.agentic/rules/`.
- Ted doplní projekt-specifická rozšíření: specifické naming konvence, stack-specifické
  typové vzory, výjimky z universal rules s odůvodněním.
- Pokud projekt nemá odchylky, file zůstane jako odkazový stub.
