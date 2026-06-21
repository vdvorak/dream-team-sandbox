---
cache_key: template-overlay-health-sensitive-data-v1.0
type: template
---

# Overlay — zdravotní / citlivá osobní data

Aplikuj pro projekty zpracovávající zvláštní kategorie osobních údajů
(GDPR čl. 9 — zdraví, biometrie ap.). Aditivní — kombinuj se `saas-web`
nebo `local-desktop` dle topologie. Watson vlije bullety do sekcí.

---

```markdown
→ Nefunkční požadavky (NFR)
- Compliance: GDPR čl. 9 (zvláštní kategorie) — vyšší laťka než běžné PII
- Šifrování citlivých dat at-rest i in-transit
- Auditovatelnost: log přístupů k citlivým datům (kdo, kdy, proč)

→ Doménová security pravidla
- Minimalizace dat: sbírat jen nezbytné; retenční politika
- Právní základ zpracování explicitní; souhlas doložitelný
- U nezletilých / nesvéprávných: souhlas zákonného zástupce
- Pseudonymizace / anonymizace kde to účel dovolí
- Přístup role-based a logovaný; princip nejmenších oprávnění

→ Doménové hard rules
- Citlivá pole nikdy v lozích, URL, cache ani analytics
- Export a výmaz dat na žádost subjektu (implementované)
- Žádné sdílení s třetími stranami bez právního základu a záznamu

→ Cílová skupina
- Počítej se zranitelnými uživateli — přístupnost i zvýšená právní ochrana
```

---

## Pozn.
Konkrétní retenční lhůty, právní základ a DPA doplní Vision/Tony s ohledem
na jurisdikci. Heimdall audituje, že citlivá pole nikam neunikají.
