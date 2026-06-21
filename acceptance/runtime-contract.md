# Acceptance criteria — runtime-contract

Každé AC = pozorovatelný PASS/FAIL. Tagger: `[security]` `[integration]`
`[automated]` `[manual E2E]`. Gate PASS = všechna AC zelená.

---

## AC-1 — Zajisti prostředí (ensure) `[integration]` `[automated]`

| # | Podmínka | PASS |
|---|---|---|
| 1a | Volání `ensure` s platným `project_id` a odkazem na repozitář | Response `200 ready` nebo `202 provisioning` s `retry_after` |
| 1b | Opakované volání `ensure` se stejným `project_id` (idempotence) | Response `200 ready`; nevznikne duplicitní prostředí |
| 1c | Souběžná volání `ensure` pro tentýž `project_id` | Výsledek = jedno prostředí; race nevrátí dvě různá `ready` |
| 1d | Volání `ensure` s neplatným / chybějícím odkazem na repozitář | Response `4xx` s chybovým kódem z app-facing registru |

---

## AC-2 — Fail-closed / ZEĎ garance `[security]` `[integration]`

| # | Podmínka | PASS |
|---|---|---|
| 2a | `ensure` dokončeno, ZEĎ je aktivní | `getEnvironment` vrátí `status: ready` |
| 2b | `ensure` dokončeno, ale enforcement nelze ověřit nebo selhal | `getEnvironment` NEVRÁTÍ `status: ready`; vrátí chybu nebo `provisioning` |
| 2c | Runtime nemůže aplikovat enforcement vůbec | `ensure` selže; nikdy `200 ready` |

---

## AC-3 — Stav prostředí + opaque připojovací adresa `[integration]` `[automated]`

| # | Podmínka | PASS |
|---|---|---|
| 3a | `getEnvironment` pro ready prostředí | Response obsahuje `connection` s neprázdnými URL hodnotami |
| 3b | `connection` URL neobsahuje substátový identifikátor (IP třídy, interní hostname schémata specifická pro konkrétní infrastrukturu) | Regex grep na response: `Fly\|docker\|6PN\|\.internal\|:808[0-9]` = 0 výskytů v `connection` poli |
| 3c | `getEnvironment` pro neexistující `project_id` | Response `404` s chybovým kódem |
| 3d | `getEnvironment` pro prostředí ve stavu `asleep` nebo `destroyed` | `connection` = `null`; stav korektně uveden |

---

## AC-4 — Uspi prostředí `[integration]` `[automated]`

| # | Podmínka | PASS |
|---|---|---|
| 4a | `sleep` na ready prostředí | Response `2xx`; stav přejde na `asleep` (nebo zůstane `ready` pokud advisory ignorováno — obojí PASS) |
| 4b | `sleep` na neexistující prostředí | Idempotentní `2xx` nebo `404` — nikdy `5xx` |

---

## AC-5 — Zruš prostředí `[integration]` `[automated]`

| # | Podmínka | PASS |
|---|---|---|
| 5a | `destroy` na existující prostředí | Response `2xx`; následné `getEnvironment` vrátí `404` nebo `status: destroyed` |
| 5b | `destroy` opakovaně (idempotence) | Response `2xx` nebo `404`; nikdy `5xx` |

---

## AC-6 — Stav repozitáře `[integration]` `[automated]`

| # | Podmínka | PASS |
|---|---|---|
| 6a | `getGitStatus` pro ready prostředí s naklonovaným repem | Response obsahuje `branch`, `dirty` (bool), `changed_files` (list), `last_commit` |
| 6b | `getGitStatus` pro prostředí kde repo nebylo naklonováno | Response `4xx` s popisem; ne `5xx` |

---

## AC-7 — Čti soubory `[integration]` `[automated]`

| # | Podmínka | PASS |
|---|---|---|
| 7a | `listFiles` bez filtru pro ready prostředí | Response obsahuje seznam souborů ve workspace |
| 7b | `listFiles` s `prefix` filtrem | Response obsahuje pouze soubory odpovídající prefixu |
| 7c | `listFiles` s cestou mimo workspace sandbox (path traversal pokus) | Response `403` s kódem path-escape; nikdy soubory mimo sandbox |

---

## AC-8 — Připoj terminál (PTY stream) `[integration]` `[manual E2E]`

| # | Podmínka | PASS |
|---|---|---|
| 8a | WebSocket `attachTerminal` na ready prostředí | Spojení etablováno; binární PTY bytes proudí obousměrně |
| 8b | Resize control zpráva (`{type:resize,rows,cols}`) přes WebSocket | Terminal reaguje na novou velikost |
| 8c | Klient se odpojí a znovu připojí (reconnect / re-attach) | Workspace proces pokračuje; session je dostupná znovu |
| 8d | `attachTerminal` na prostředí ve stavu jiném než `ready` | WS close s chybovým kódem; nikdy tiché selhání |

---

## AC-9 — Zdravotní dotaz (healthz) `[automated]`

| # | Podmínka | PASS |
|---|---|---|
| 9a | `GET /v1/healthz` | Response `200` s `status` a `contract_version` |
| 9b | `contract_version` odpovídá vendorované verzi v aplikaci | Drift-check v CI neprojde pokud se liší |

---

## AC-10 — Standalone usability (generický klient bez aplikace) `[manual E2E]`

Scénář: generický klient (curl + websocat nebo ekvivalent) projde plný flow
bez jakéhokoli kódu aplikace.

| Krok | Akce | PASS |
|---|---|---|
| S1 | `ensure` s libovolným `project_id` + repo URL | Dosáhne `ready` |
| S2 | `getEnvironment` | Vrátí `connection` s neprázdnými URL |
| S3 | `listFiles` | Vrátí soubory workspace |
| S4 | `getGitStatus` | Vrátí git metadata |
| S5 | `attachTerminal` přes WebSocket | PTY stream funguje, lze zadat příkaz |
| S6 | `destroy` | Prostředí zrušeno; následný `getEnvironment` = 404/destroyed |

Podmínka standalone: žádný krok nevyžaduje aplikační kód ani applikační identitu
specifickou pro aplikaci — stačí autentizační identita servisu a `project_id`.

---

## AC-11 — Agnostika kontraktu (žádný substrát-noun v ploše) `[security]` `[automated]`

| # | Podmínka | PASS |
|---|---|---|
| 11a | Grep všech response polí v OpenAPI schématu | Žádné `Fly\|Docker\|nftables\|6PN\|tmux\|WORKSPACE_AGENT_BASE` v názvech polí ani enum hodnotách |
| 11b | Grep chybového registru (app-facing) | Žádný substát-specifický identifikátor v chybových kódech |
| 11c | `connection` URL parsovatelné bez znalosti substrátu | URL je opaque string; klient ho použije přímo bez modifikace |

---

## AC-12 — ZEĎ-disjunktnost (kontrakt nezmírňuje enforcement) `[security]`

| # | Podmínka | PASS |
|---|---|---|
| 12a | Revize kontraktní plochy (OpenAPI) | Žádný parametr, query-string ani tělo request/response neumožňuje nastavit, zmírnit nebo zjistit egress allowlist / ingress config / shell omezení |
| 12b | Žádná operace nevrací detaily ZDI (ruleset, proxy config, capability seznam) | Grep schématu → 0 výskytů policy/ruleset/allowlist/capability jako response pole |
| 12c | Pokus o `ensure` s parametrem ovlivňujícím enforcement | Request selže validací nebo je parameter ignorován; nikdy nezpůsobí oslabení ZDI |

---

## AC-13 — BYOK token neteče přes control API `[security]`

| # | Podmínka | PASS |
|---|---|---|
| 13a | Revize OpenAPI schématu a chybového registru | Žádné pole nepřijímá ani nevrací AI tool token nebo ekvivalentní credential |
| 13b | Token vstupuje výhradně interaktivně přes PTY session | Verifikace architekturou / code review; token není součástí HTTP request/response |

---

## AC-14 — Auth odběratele `[security]` `[integration]`

| # | Podmínka | PASS |
|---|---|---|
| 14a | Volání bez platné identity odběratele | Response `401` s kódem `ERR_UNAUTHORIZED`; nikdy `5xx` |
| 14b | Volání s platnou identitou | Operace provedena (nebo jiná business chyba — nikdy `401`) |

---

## Mapování schopností → AC

| Schopnost | AC |
|---|---|
| Zajisti prostředí | AC-1, AC-2 |
| Stav prostředí | AC-3 |
| Uspi prostředí | AC-4 |
| Zruš prostředí | AC-5 |
| Stav repozitáře | AC-6 |
| Čti soubory | AC-7 |
| Připoj terminál | AC-8 |
| Healthz | AC-9 |
| Standalone usability | AC-10 |
| Agnostika | AC-11 |
| ZEĎ-disjunktnost | AC-12 |
| BYOK neteče | AC-13 |
| Auth | AC-14 |
