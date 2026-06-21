---
cache_key: template-project-constitution-v1.1
type: template
---

# Project Constitution template

Watson seeduje root `PROJECT-CONSTITUTION.md` z tohoto templatu (greenfield),
nebo do něj migruje obsah existující ústavy (transition). Žije v **rootu
projektu** — je to projekt-specifická ústava, NE framework.

Rozdíl od `.agentic/constitution.md`:
- `.agentic/constitution.md` = **universal** (framework principy, JAK agenti
  fungují) — synced z dream-team, needitovat
- `PROJECT-CONSTITUTION.md` (root) = **projekt-specifická** (CO projekt je) —
  vlastní Vision/Tony/Ted, per-projekt, nesynchronizuje

Změna PROJECT-CONSTITUTION = **L3** (fundament projektu).

---

```markdown
# <Project> — Project Constitution

Projektová ústava. Doplňuje universal `.agentic/constitution.md` o to,
CO tento projekt je. Při konfliktu má v doménách níže přednost před universal.

## Vize a mise   <!-- vlastní Vision -->
<1–3 věty: co projekt dělá, proč, jaký je dlouhodobý cíl>

## Hodnoty   <!-- Vision + Tony -->
- <hodnota 1 — co je pro projekt nejdůležitější>
- <hodnota 2>

## Cílová skupina   <!-- Vision -->
<kdo to používá: B2B/B2C/interní, persona>

## Co projekt JE / NENÍ   <!-- Vision -->
**Je:** <vymezení scope>
**Není:** <explicitní out-of-scope — brání scope creepu>

## Nefunkční požadavky (NFR)   <!-- Tony + Ted -->
- **Bezpečnost**: <šifrování, auth, citlivá data>
- **Performance**: <SLA, p95 cíle pro kritické cesty>
- **Dostupnost**: <uptime, je/není life-critical>
- **Compliance**: <GDPR / HIPAA / PCI / žádné>
- **Lokalizace**: <i18n od začátku? default jazyk>

## Doménová security pravidla   <!-- Tony, Heimdall input -->
<projekt-specifické: forbidden v logu, šifrování klíčů, threat model>

## Delivery topologie   <!-- Tony + Ted -->
<targets: server/web/mobile/desktop; deployment model; per-instance vs SaaS>

## Doménové hard rules   <!-- dle potřeby -->
<pravidla specifická pro tuto doménu, která nejsou v universal constitution>
```

---

## Type-specific overlays

Base template výše je **prázdná struktura** — žádný pre-fill bezpečnosti.
Universal pravidla jsou v `.agentic/constitution.md` (needuplikovat zde);
projekt-specifický obsah doplní Vision/Tony/Ted.

„Společné, ale ne-universal" pravidla (platná pro celou *třídu* projektů)
žijí v `templates/constitution-overlays/`. Watson podle typu projektu
aplikuje relevantní overlay — vlije jeho keyed bullety do odpovídajících
sekcí níže. Overlays jsou **aditivní a kombinovatelné** (health SaaS web =
`saas-web` + `health-sensitive-data`).

| Typ projektu | Overlay | Plní sekce |
|---|---|---|
| multi-tenant SaaS web | `saas-web` | NFR, Doménová security, Topologie, Hard rules |
| lokální desktop (offline) | `local-desktop` | NFR, Doménová security, Topologie, Hard rules |
| WordPress / headless CMS | `wordpress-cms` | NFR, Topologie, Hard rules, Doménová security |
| zdravotní / citlivá data | `health-sensitive-data` | NFR, Doménová security, Hard rules, Cílová skupina |

Vyšší vrstva vyhrává: pokud overlay/ústava určí např. SSR pro SEO,
**přebíjí** `rules/frontend` CSR default.

## Pozn. pro Watson

- **Greenfield**: vyplň z interview (vize z fáze 1, NFR/compliance z fáze 4,
  topologie z fáze 2) + aplikuj relevantní overlay(s) dle typu projektu.
  Sekce nech jako TODO kde info chybí.
- **Transition**: pokud existuje root `CONSTITUTION.md` (nebo `ORCHESTRATION.md`
  s projekt-specifickým obsahem), **migruj** jeho doménový obsah sem
  (vize, hodnoty, NFR, topologie). Generická workflow mechanika se NEmigruje
  (ta je v `.agentic/flow.md`). Po migraci lze starý soubor sunsetnout (L3).
