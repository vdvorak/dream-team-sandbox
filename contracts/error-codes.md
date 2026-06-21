---
type: error-code-registry
owner: ted-architect
---
# Error code registry — containment-cage

Centrální registr error codes klece. Producent = cage-deploy obálka / host-policy applier /
overlay entrypoint. Konzument = operátor (deploy log) + observability. **Vše fail-closed:**
každý error níže znamená "enforcement nelze aplikovat/ověřit" → deploy NEDOKONČEN nebo runtime DENY.

| code | vrstva / fáze | trigger | chování | invariant |
|---|---|---|---|---|
| `ERR_NO_POLICY` | deploy / vrstva 2 | chybí kompletní ruleset H1–H7 před spuštěním machine | deploy ABORT | I1 |
| `ERR_POLICY_APPLY_FAILED` | deploy / vrstva 2 | host-enforced policy API selhalo při apply | deploy ABORT | I1 |
| `ERR_CAGE_DRIFT` | deploy / overlay | `WORKSPACE_DEF_HASH` neshoda od posledního cage-deploy | deploy FAIL + upozornění; vyžaduje `--accept-drift` re-pin | I11 |
| `ERR_PROXY_DOWN` | runtime / vrstva 1 | Smokescreen sidecar nedostupný | fail-CLOSED (žádný egress; NE bypass); observability alert | I2 |
| `ERR_INVM_FW_FAILED` | runtime / vrstva 3 | in-VM nftables instalace selhala (entrypoint krok 1) | entrypoint ABORT, machine se nespustí jako klec | I4 |
| `ERR_CAP_DROP_FAILED` | runtime / de-root | drop `CAP_NET_ADMIN` z bounding setu selhal (krok 2) | entrypoint ABORT, NIKDY exec agenta s root caps | I4 |
| `ERR_NNP_FAILED` | runtime / de-root | `no_new_privs=1` se nepodařilo nastavit (krok 3) | entrypoint ABORT před exec agenta | I6 |
| `ERR_INGRESS_LEAK` | deploy / overlay lint | `[http_service]` nalezen v overlay `fly.workspace.toml` | deploy ABORT | I7 |
| `ERR_SECRET_LEAK` | deploy / pre-scan | high-value secret v workspace env/volume | deploy ABORT | I9 |
| `ERR_GIT_WRITE_CRED` | deploy / pre-scan | git write credential nalezen ve workspace (regrese rozhodnutí (b)) | deploy ABORT | I10 |
| `ERR_LOGIN_PERSIST` | post-deploy smoke | Claude login token se neuložil/nepřežil restart po de-root | smoke FAIL (regrese-guard), re-review entrypoint chown/symlink | regrese-guard §1 |

Pozn.: `ERR_UNKNOWN_TOOL` (terminál) patří appce (`terminal_router.py`), NE kleci — mimo tento registr.
