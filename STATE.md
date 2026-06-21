# STATE.md — dream-team-sandbox

<!-- ENGINE:STATE START -->
closed_waves: []
<!-- ENGINE:STATE END -->

## Aktualni fokus

⏸️ **PAUZA (2026-06-21) — zmena smeru aplikace.** Wave `2026-06-21-containment-cage`
zastaven v T3 na zadost uzivatele: dream-team-app meni smer. Protoze klec obaluje
runtime workspace appky (threat actor = workspace-container AI), zmena smeru appky
muze vyzadovat prepracovani scope/threat-modelu klece PRED pokracovanim. Nic nenasazeno
(zamerne — deploy se nedelal). Vsechny artefakty commitnute + pushnute.

### Postup wave (completed nodes)
- **T1 HOTOVO:** intake PASS · product PASS (spec+acceptance, I1-I11 otagovane;
  2x spec-gate FAIL na agnostiku → opraveno) · spec-gate PASS · feasibility PASS
  (Tony: obe diry potvrzeny v kodu; I8/I9 uz drzi; zadny git write credential ve
  workspace dnes).
- **T2 HOTOVO:** architecture PASS (Ted: 3-vrstvy enforcement H1-H7, de-root sekvence
  0-4, overlay+drift, 11 error codes, rules CE-1..CE-9) · backend PASS (Bob: implementace
  v `server/cage/**` + overlay artefakty, 58 unit testu) · code-lint PASS (F401 fixnuto).
- **T3 ROZPRACOVANO:** qa — joey postavil acceptance harness + 128/128 statickych testu
  PASS (integration/overlay/regression); 32 zivych AC bodu `[post-deploy-live]` BLOCKED
  na deploy. Node `qa` zustava inflight (nezuzavren — gate nelze uzavrit bez zivého deploye).

### Zavazna rozhodnuti provozovatele (zapecena do architektury)
- Git credential: workspace NIKDY nedostane git write credential (I10 = silnejsi invariant).
- Deploy: cage-deploy = jedina cesta + drift-detekce (hash workspace image definice).
- DNS resolver IP + metadata CIDR = spike-to-confirm (heimdall) — zatim parametry s defaulty.
- CF Access team domena = injektnuta pri deploy z env, ACL sablonovana.

## Open Items (po vyjasneni smeru appky)

- [ ] **ROZHODNOUT:** ovlivnuje zmena smeru dream-team-app threat model/scope klece?
      (workspace-container AI = threat actor; pokud se workspace mechanika meni → revize)
- [ ] heimdall-security (security node, T3): adversarialni audit klece + Fly spike
      (Network Policy API tvar, capability drop v microVM, DNS resolver IP, metadata CIDR)
- [ ] vitek-quality (code-quality node, T3): 423 advisory nalezu z lintu (docstrings,
      anotace, E501) — posoudit ktere jsou blocking
- [ ] optimus-perf (performance node, T3)
- [ ] alfred-devops (devops node, T4): wire realne fly/docker prikazy do injection pointu
      cage-deploy (Bob nechal jako callable), staging deploy
- [ ] deploy-approve (L3 human gate) → production → live acceptance suite (harness I1-I11)
- [ ] spike-param duplikace (ruleset.py + nftables.cage.conf) — sjednotit po heimdall spike
