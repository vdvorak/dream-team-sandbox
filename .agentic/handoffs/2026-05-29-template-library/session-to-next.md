---
wave: 2026-05-29-template-library
from: session
to: user
type: spec-completed
returns_to: null
timestamp: 2026-05-29T00:00:00+02:00
---

# Handoff: Planning session → Příští session (implementace)

## Stav

Session proběhla jako discovery + návrh — žádný kód nebyl psán, žádné templates
zatím nevznikly. Probrali jsme 5 reálných projektů (murio, UnagyDev, Parker2,
pneukarnik, Vdoklad) a zmapovali co v template systému chybí.

Opravena drobnost: VERSION file byl na 0.5.6 přestože git byl na 0.5.9 — opraveno.

## Plán (co bylo navrženo)

1. Zmapovat stávající rules/stacks/constitutions napříč 5 projekty
2. Identifikovat co je boilerplate (copy-paste) vs. genuinně unikátní
3. Navrhnout strukturu template knihovny

## Výsledek

- `STATE.md` — vytvořen (nový soubor, wave 2026-05-29-template-library)
- `handoffs/2026-05-29-template-library/` — adresář vytvořen
- `VERSION` — opraven 0.5.6 → 0.5.9

**Navržena template knihovna** (žádný soubor zatím nevznikl):

| Adresář | Obsah | Zdrojové projekty |
|---|---|---|
| `templates/rules/` | programming, backend, frontend, error-responses, logging | murio ≈ Parker2 (téměř identické) |
| `templates/stacks/python-fastapi-postgres.md` | async FastAPI + PostgreSQL | murio, Parker2 |
| `templates/stacks/python-fastapi-sqlite.md` | sync FastAPI + SQLite + PyInstaller | Vdoklad |
| `templates/stacks/java-quarkus-postgres.md` | Java 21 + Quarkus + jOOQ + Gradle | UnagyDev |
| `templates/stacks/solidjs-web.md` | SolidJS + TS + openapi-fetch | murio, Parker2 |
| `templates/stacks/solidjs-electron.md` | Electron + SolidJS + CSS Modules | Vdoklad |
| `templates/stacks/wordpress.md` | WordPress + custom plugin | pneukarnik |
| `templates/constitution-overlays/saas-web.md` | multi-tenant NFR, JWT, GDPR SaaS | murio, UnagyDev, Parker2 |
| `templates/constitution-overlays/local-desktop.md` | offline-first, local data, packaging | Vdoklad |
| `templates/constitution-overlays/wordpress-cms.md` | headless CMS, SEO hard rules | pneukarnik |
| `templates/constitution-overlays/health-sensitive-data.md` | GDPR čl. 9, vulnerabilní uživatelé | UnagyDev (Unagy) |

**Existující template obohatit:**
`templates/project-constitution.md` — předvyplnit security rules + hard rules sekce
(dnes prázdné placeholders, ale obsah je identický ve všech projektech).

## Decided

- **Žádní tech-specific agenti** — Bob zůstává obecný backend agent; technologické
  principy jdou do `templates/stacks/` a `rules/`, ne do specializovaných agentů.
  Důvod: O(n) maintenance overhead bez přidané hodnoty; principy jsou přenositelné.
- **Rules templates jsou kopírovatelné defaults** — Watson zkopíruje do projektu,
  projekt customizuje jen kde se skutečně liší. Není to lock-in.
- **Constitution overlays jsou additive** — base template + vybrané overlays dle
  detekovaného typu projektu; Watson aplikuje při setup interview.

## Slabé místo

- Stack templates jsou velké soubory (viz UnagyDev stack/server.md — stovky řádků
  projekt-specifických detailů). Template musí být **obecný základ**, ne kopie
  existujícího projektu. Riziko: přenést příliš projekt-specifický obsah do templates.
  Řešení: templates obsahují jen obecné principy + strukturu; projekt-specifické
  detaily (konkrétní verze, třídy, patterns) se doplní při setupu / T2 wave.
- Watson update (fáze 5 interview) — jak moc explicitně se ptát na typ projektu
  (SaaS/desktop/WordPress) vs. odvodit z tech stack odpovědí? Otevřené.

## Normativní mezera

- **Co chybí**: Watson interview fáze 2 neobsahuje otázku na "typ projektu"
  (SaaS / local desktop / CMS / …), která by triggerovala constitution overlays
- **Kde chybí**: `agents/watson-interviewer.md` §Fáze 2 / §Fáze 4
- **Kdo dodá**: uživatel rozhodne, Watson se aktualizuje (Eywa)

## === GATE OUTPUT ===
```
agent: session
phase: T1
planning-complete: OK
write-scope: RESPECTED
returns-to: user
weak-spot: stack templates nesmí být kopie existujících projektů — jen obecný základ
next-action: implementovat templates/rules/ jako první (nejmenší, nejvyšší ROI)
```
==================
