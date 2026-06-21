---
cache_key: template-overlay-local-desktop-v1.0
type: template
---

# Overlay — lokální desktop (offline-first)

Aplikuj pro desktop aplikace s lokálními daty, funkční bez sítě. Watson
vlije bullety do sekcí `PROJECT-CONSTITUTION.md`.

---

```markdown
→ Nefunkční požadavky (NFR)
- Offline-first: core funkce fungují bez síťového připojení
- Lokální vlastnictví dat: data zůstávají u uživatele, ne v cloudu
- Dostupnost = lokální spolehlivost (žádné uptime SLA serveru)
- Výkon: svižnost na běžném uživatelském HW, ne serverový profil

→ Doménová security pravidla
- Citlivá lokální data šifrovaná at-rest
- Žádná telemetrie ani odesílání dat bez explicitního souhlasu uživatele

→ Delivery topologie
- Distribuce přes instalátory (Windows / macOS / Linux)
- Auto-update kanál; podpisy/notarizace per platforma
- Per-uživatel instalace, lokální datové úložiště

→ Doménové hard rules
- Žádný povinný cloud roundtrip pro core funkcionalitu
- Sync (pokud je) je volitelný a explicitní, ne tichý
```

---

## Pozn.
Pro Electron viz stack `_target/electron` (bezpečný IPC) + `_db/sqlite`
(lokální data). Konkrétní šifrování a update kanál doplní Tony/Winny.
