---
type: app-runtime-contract
owner: ted-architect
status: v1 (initial)
contract_version: "1.1.0"
api: contracts/api/runtime.openapi.yaml
constitution: PROJECT-CONSTITUTION.md §Kontrakt app↔runtime
related-but-separate: contracts/error-codes.md (INTERNÍ cage registr — NEMÍCHAT)
---
# Kontrakt app↔runtime

> Stabilní, substrátem-agnostická hranice mezi **RUNTIME** (`dream-team-sandbox`) a jeho
> odběratelem (**APLIKACE** nebo generický klient). Fyzicky vlastněn tímto repem; odběratel
> ho vendoruje read-only. Změna = koordinovaný L3. *Architecture is forever.*

## 1. Princip

Odběratel řídí **stavový automat nad jediným nounem `Environment`** a dostane **opaque
connection handle**. Tři tvrdé linie:

1. **Opacita.** Odběratel vidí jen kontrakt. Nevidí dovnitř runtimu — substrát, image, agent,
   enforcement, fd, volume layout jsou neviditelné. `connection` jsou **opaque URL stringy**:
   odběratel je použije beze změny a z nich nezjistí, na čem prostředí běží.
2. **Runtime nezná odběratele.** Vystavuje jen tento kontrakt. Funguje standalone (curl + WS
   klient), bez aplikačního kódu — stačí service identita a `project_id`.
3. **ZEĎ je vlastnost prostředí, ne parametr.** Kontrakt nemá žádnou operaci, query, hlavičku
   ani pole, kterým by šlo zmírnit, nastavit nebo přečíst egress / ingress / shell enforcement.
   Odběratel ZEĎ přes kontrakt **nemůže oslabit** (viz §6).

Transport = **HTTP+JSON / OpenAPI 3.1** (control) + **WebSocket** (PTY data plane). Ne gRPC:
PTY binární stream přes WS už je ověřený, curl-ovatelnost nese standalone, OpenAPI je strojově
ověřitelný společný artefakt + drift-check fixture.

## 2. Resource & lifecycle model

**Noun `Environment`** — 1:1 s projektem. Identita = **opaque `project_id`** (`^[A-Za-z0-9_-]+$`,
1–128 znaků). Runtime `project_id` nijak neinterpretuje; je to jen klíč.

**Stavový automat:**

```
none ──ensure──► provisioning ──(ZEĎ aktivní)──► ready ──sleep──► asleep
                      │                            │  ▲             │
                      │                            │  └──ensure─────┘
                      ▼ (enforcement nelze)        ▼
                 (chyba, NE ready)             destroyed ◄──destroy── (z kteréhokoli stavu)
```

| stav | význam | `connection` |
|---|---|---|
| `none` | neexistuje (nikdy nevzniklo / `getEnvironment` → 404) | — |
| `provisioning` | vzniká nebo se probouzí; ZEĎ ještě neověřena | `null` |
| `ready` | aktivní **a ZEĎ je aktivní** (fail-closed garance) | neprázdné URL |
| `asleep` | advisory uspáno; lze znovu `ensure` | `null` |
| `destroyed` | nevratně zrušeno | `null` |

- **`phase`** = volný podstav uvnitř `provisioning` (`cloning`, `enforcing`, `booting`, …);
  čistě informativní pro retry UX, **ne** součást garance ani enum kontraktu (tolerant reader).
- **Idempotence.** `ensure` na existující ready prostředí vrátí totéž (žádný duplikát). `sleep`
  a `destroy` jsou idempotentní (opakování nikdy `5xx`).
- **Serializace per `project_id`.** Souběžné `ensure` pro tentýž projekt runtime serializuje →
  vznikne **jedno** prostředí; race nikdy nevrátí dvě různá `ready`.
- **Clone složený do `ensure`.** Repozitář se klonuje jako součást `ensure` (ruší dřívější
  lazy-clone duplikaci a `repo_not_ready` race). `ensure` nese `repo:{url, ref?}`; opakovaný
  `ensure` se stejným `url` je no-op-sync, s **jiným** `url` na živém prostředí → `ERR_REPO_MISMATCH`
  (jedno prostředí = jeden repozitář; přepnutí repa = `destroy` + `ensure`).

## 3. Auth / trust — tři disjunktní vztahy

| vztah | mechanismus | poznámka |
|---|---|---|
| **User → App** | CF-Access | **app-interní**, runtime ho vůbec nevidí ani nevyžaduje |
| **App → Runtime** | **mTLS** (primární); fallback **service token** (app-side `Authorization: Bearer`) | autentizuje odběratele vůči control/data plane. Selhání → `401 ERR_UNAUTHORIZED`, nikdy `5xx` |
| **BYOK token → AI tool** | **interaktivní login v PTY session** | token AI nástroje **NIKDY** neteče přes control API. Runtime je **vodič, ne trezor**: žádné pole control plane token nepřijímá ani nevrací. Volitelný ephemeral per-session vstup je výhradně uvnitř PTY streamu (§5), nepersistuje se. |

Standalone klient používá tentýž **App→Runtime** mechanismus (service identita) — nepotřebuje
žádnou aplikačně-specifickou identitu (AC-10, AC-14).

## 4. ZEĎ-disjunktnost a fail-closed garance

- **Disjunktnost.** Žádná operace/parametr/query/hlavička/pole nezmírňuje, nenastavuje ani
  neodhaluje egress allowlist, ingress config, shell omezení ani capability seznam. Pokus o
  takový parametr je validací odmítnut nebo ignorován — nikdy nezpůsobí oslabení ZDI (AC-12).
- **Fail-closed garance (load-bearing):** **runtime NIKDY nevrátí `status: ready` bez aktivní
  ZDI.** Pokud enforcement nelze aplikovat ani ověřit → prostředí zůstane v `provisioning`,
  `ensure` selže, nebo runtime vrátí `503 ERR_RUNTIME_UNAVAILABLE`. `ready` ⟹ ZEĎ aktivní je
  invariant kontraktu, ne implementační detail (AC-2).
- **Nepropustnost interních chyb.** Interní cage chybové kódy (`contracts/error-codes.md`:
  `ERR_NO_POLICY`, `ERR_PROXY_DOWN`, `ERR_INVM_FW_FAILED`, …) se **nikdy** nepromítnou do
  app-facing roviny. Navenek se selhání enforcement projeví výhradně jako `ERR_RUNTIME_UNAVAILABLE`
  / `provisioning` / `ERR_PROVISION_FAILED` — odběratel nezjistí důvod uvnitř ZDI.

## 5. Data plane — terminál (WS)

`attachTerminal` (`GET /v1/environments/{project_id}/terminal?tool=`) — viz `x-websocket` v
OpenAPI (3.1 WS nemodeluje nativně).

- **Binární PTY bytes** obousměrně (`message` frames typu binary = raw PTY I/O).
- **Text control:** JSON `{type:"resize", rows:<int>, cols:<int>}` (text frame). Jediná
  podporovaná control zpráva; neznámý `type` se ignoruje (tolerant reader).
- **Reconnect / re-attach.** Uzavření WS prostředí **neruší**; workspace proces běží dál.
  Klient se znovu připojí ke stávající session (AC-8c).
- **Close kódy:**

| kód | význam |
|---|---|
| `4401` | neautentizováno (mTLS/token selhal) — analogie `ERR_UNAUTHORIZED` |
| `4404` | prostředí neexistuje — analogie `ERR_ENVIRONMENT_NOT_FOUND` |
| `4400` | prostředí není `ready` / nevalidní `tool` — analogie `ERR_ENVIRONMENT_NOT_READY` / `ERR_TOOL_NOT_ALLOWED` |
| `1011` | interní chyba runtimu (standardní WS) |

Nikdy tiché selhání: nelze-li attachnout, WS se zavře s konkrétním kódem (AC-8d).

## 6. Versioning

- **SemVer.** `contract_version` (aktuálně `"1.1.0"`) vrací `healthz` i každý `environment` objekt.
  Cesta nese MAJOR: `/v1`.
- **Changelog:** `1.1.0` (MINOR, non-breaking) přidalo app-facing kód `ERR_INVALID_REQUEST` (`400`,
  schema-validace request body) — viz §8. Tolerant reader appky beze změny snese (žádný L3).
- **Non-breaking** (PATCH/MINOR, bez koordinace): přidání **optional** pole, nové operace, nového
  error kódu, nové `phase` hodnoty. Odběratel je **tolerant reader** (ignoruje neznámá pole).
- **Breaking** (MAJOR, **koordinovaný L3 v obou repech**): odebrání/přejmenování pole, změna typu,
  zúžení enumu, nové **required** pole, změna sémantiky stavu. Nový major běží jako **`/v2` vedle
  `/v1`** — žádný flag-day; obě strany se koordinují před nasazením.
- OpenAPI artefakt = contract-test fixture + **drift-check v CI obou repů** (`healthz.contract_version`
  vs vendorovaná verze — neshoda = CI fail, AC-9b).

## 7. Out-of-contract (NESMÍ leaknout do kontraktní plochy)

Tyto nouny/koncepty jsou výhradně interní runtimu a **nesmí** se objevit v názvech polí, enum
hodnotách, error kódech ani `connection` URL (AC-11, AC-12b):

- Substrát: `Fly`, `Docker`, `AWS`, `6PN`, `.internal`, microVM, public IP, `*.fly.dev`, port `:808x`.
- ZEĎ internals: `nftables`, Smokescreen/proxy, ruleset H1–H7, CIDR/allowlist, de-root sekvence,
  `CAP_NET_ADMIN`, `no_new_privs`, seccomp, capability seznam, policy/ruleset jako response.
- MOTOR internals: image build, `Dockerfile.workspace`, `entrypoint.sh`, drift / `WORKSPACE_DEF_HASH`,
  `WORKSPACE_AGENT_BASE`, tmux, PTY fd, volume layout.
- Interní cage error kódy (`contracts/error-codes.md`) — viz §4 (nepropustnost).

Navenek se za nimi nachází jen: stav (`status`/`phase`), **opaque** `connection` URL a app-facing
error registr (§8).

## 8. App-facing error registr

> **ODDĚLENÝ** od interního cage registru `contracts/error-codes.md` (ten zůstává interní,
> producent = cage-deploy/host-policy/overlay; konzument = operátor). Tenhle registr je
> **sdílený s aplikací** (vendorovaný). Žádný kód se nepřekrývá; žádný substrát-noun (AC-11b).

**Envelope** (sdílený s appkou, identický shape jako app error model):

```json
{ "code": "ERR_…", "message": "human-readable", "detail": { } }
```

| code | HTTP | trigger | poznámka |
|---|---|---|---|
| `ERR_INVALID_REQUEST` | `400` | request body nesplňuje schéma: **neznámé/zakázané pole** (`additionalProperties:false`, vč. enforcement-bypass pole kdekoli v body i v `repo.*`), chybějící **required** pole, špatný typ, nevalidní tvar `repo.url` | schema-validační selhání; NIKDY tiché přijetí (AC-12c). Disjunktní od `ERR_TOOL_NOT_ALLOWED` (to je business allowlist `tool`, ne schéma) |
| `ERR_ENVIRONMENT_NOT_FOUND` | `404` | operace na neexistující `project_id` | WS analogie close `4404` |
| `ERR_ENVIRONMENT_NOT_READY` | `409` | operace vyžadující `ready` na prostředí v jiném stavu (git/files/terminal) | |
| `ERR_ENVIRONMENT_DESTROYING` | `409` | operace na prostředí, které se právě ruší | |
| `ERR_REPO_MISMATCH` | `409` | `ensure` s jiným `repo.url` na živém prostředí | jedno prostředí = jeden repozitář |
| `ERR_CLONE_FAILED` | `422` | klonování repa **selhalo za běhu** (syntakticky validní, ale nedostupný/neexistující `url`/`ref`) | AC-1d, AC-6b. NE schema-chyba (ta je `ERR_INVALID_REQUEST` 400) |
| `ERR_PROVISION_FAILED` | `502` | provisioning selhal (vč. neaplikovatelné ZDI — bez interního detailu) | fail-closed; viz §4 |
| `ERR_PATH_ESCAPE` | `403` | `listFiles` cesta mimo workspace sandbox (path traversal) | AC-7c |
| `ERR_TOOL_NOT_ALLOWED` | `400` | nepodporovaný `tool` v `ensure`/`terminal` (business allowlist, NE schéma) | WS analogie close `4400` |
| `ERR_UNAUTHORIZED` | `401` | chybí/neplatná App→Runtime identita (mTLS/token) | nikdy `5xx`; WS close `4401` |
| `ERR_RUNTIME_UNAVAILABLE` | `503` | runtime nemůže obsloužit / enforcement nelze ověřit | fail-closed default |

> **Hranice `400` kódů (load-bearing).** `ERR_INVALID_REQUEST` = **schéma** body nesedí (neznámé/zakázané
> pole, chybějící required, špatný typ). `ERR_TOOL_NOT_ALLOWED` = body je schématicky validní, ale
> hodnota `tool` není v business allowlistu. Obě `400`, ale disjunktní trigger; enforcement-bypass pokus
> (`firewall`/`egress`/`policy` kdekoli v body) je vždy schema-chyba → `ERR_INVALID_REQUEST`.

**Žádný kód nepřijímá ani nevrací AI tool token či jiný BYOK credential** (AC-13a).

## 9. Vlastnictví

Kontrakt (`contracts/runtime-contract.md` + `contracts/api/runtime.openapi.yaml`) fyzicky žije
v **`dream-team-sandbox`**. Do `dream-team-app` se **vendoruje / submoduluje read-only** + CI
drift-check (`contract_version`). Runtime je jediný autoritativní zdroj; app je read-only
konzument. Změna = **koordinovaný L3** ve více repech (§6).

## 10. Mapování schopnost → operace → AC

| Schopnost (spec) | Operace | AC |
|---|---|---|
| Zajisti prostředí | `POST …/ensure` | AC-1, AC-2 |
| Stav prostředí | `GET …/{project_id}` | AC-3 |
| Uspi prostředí | `POST …/sleep` | AC-4 |
| Zruš prostředí | `DELETE …/{project_id}` | AC-5 |
| Stav repozitáře | `GET …/git` | AC-6 |
| Čti soubory | `GET …/files` | AC-7 |
| Připoj terminál | `GET …/terminal` (WS) | AC-8 |
| Healthz | `GET /v1/healthz` | AC-9 |
| Standalone | (všechny přes service identitu) | AC-10 |
| Agnostika / ZEĎ-disjunktnost / BYOK / Auth | §4, §7, §3, §8 | AC-11..14 |
