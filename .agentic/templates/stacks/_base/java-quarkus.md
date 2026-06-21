---
cache_key: template-stack-java-quarkus-v2.0
type: template
---

# Stack — Java + Quarkus + jOOQ + PostgreSQL (kanonický reference)

**Zlatý standard** pro server target v tomto stacku. Watson seeduje obsah níže
(po `---` až po `## Pozn.`) do projektového `stack/server.md`; doplní reálnou
kostru z `templates/scaffolds/java-quarkus/`. Cíl: **dva java projekty vypadají
strukturou i syntaxí skoro identicky.**

Tech-agnostic pravidla viz `rules/backend.md`. Hygiena viz `constitution.md`.
Tento stack je **PostgreSQL-coupled** (jOOQ generuje z Postgres schématu) —
`_db/postgres` fragment se pro něj nepřidává, je integrální zde.

Odchylka od tohoto referenceu = vědomé rozhodnutí (Ted), ne drift.

---

## Technologie

- **Java 21**, Gradle (wrapper autoritativní)
- **Quarkus** — REST (`quarkus-rest`, `quarkus-rest-jackson`)
- **jOOQ** — type-safe SQL, generováno z DB schématu (`org.jooq:jooq:3.19.x`)
- **JDBC + PostgreSQL** — `quarkus-jdbc-postgresql`
- **Flyway** — migrace (`contracts/db/migrations/`, spouští Quarkus při startu)
- **SmallRye JWT** — RS256 (`quarkus-smallrye-jwt`, `-build`)
- **quarkus-hibernate-validator** — Bean Validation
- **quarkus-arc** (CDI), **quarkus-security**, **quarkus-smallrye-openapi**
- **BCrypt** — `BcryptUtil` z `quarkus-elytron-security-common`
- **quarkus-mailer** + **Qute** (pokud projekt posílá maily)

Verze: Quarkus + Gradle pinned v `gradle.properties`. Pouze deklarované
knihovny (constitution) — nová závislost vetted (Tony/Heimdall).

## Module struktura

```
src/main/java/<base-package>/
├── DatabaseProducer.java       # CDI producer pro jOOQ DSLContext
├── shared/                     # cross-cutting infra (viz Sdílená infrastruktura)
│   ├── ApiException.java  ApiExceptionMapper.java  ValidationExceptionMapper.java
│   ├── BaseResource.java
│   ├── Api{View,Data,ExtData,ListOf,PageOf,SliceOf}.java
│   └── model/{ErrorResponse,ValidationResult}.java
└── <feature>/
    ├── resource/   # JAX-RS endpointy; třída extends BaseResource
    ├── service/    # business logika
    ├── repository/ # jOOQ DB přístup
    └── model/      # request/response POJO/record
```

Vrstvení a hranice viz `rules/backend.md` (Router→Service→Repository). Resource
= JAX-RS transport; service = logika bez HTTP/SQL; repository = jediný jOOQ přístup.

## jOOQ generování (build pipeline)

Plugin `nu.studer.jooq`. Postup při buildu:
1. `concatMigrations` spojí SQL z `contracts/db/migrations/` (seřazeno `V<n>__`)
2. jOOQ generator spustí Postgres přes TestContainers JDBC a vygeneruje třídy
   (`jdbc:tc:postgresql:16:///app?TC_INITSCRIPT=file:<abs>/all-migrations.sql`)
3. Generated do `build/generated-sources/jooq`, package `<base-package>.db`
4. `compileJava.dependsOn(generateJooq)`

Důležité: `TC_INITSCRIPT` musí mít `file:` prefix před absolutní cestou.
`build/generated-sources/jooq/**` = build output, needituje se, nepatří do repa.
`contracts/db/migrations/**` = server-owned kontrakt (source of truth).

## Konfigurace (`application.properties`)

- `quarkus.rest.path=/api/v1` (dle `servers[0].url` v OpenAPI)
- `quarkus.datasource.db-kind=postgresql`; jdbc.url jen v `%dev`/`%prod`
  (v default profilu NE — jinak DevServices nespustí test container)
- `quarkus.flyway.migrate-at-start=true`
- JWT: `smallrye.jwt.sign.key.location`, `mp.jwt.verify.publickey.location`,
  `mp.jwt.verify.issuer`, `smallrye.jwt.new-token.{issuer,lifespan}`
  (pozor prefix `smallrye.jwt.new-token`, ne `quarkus.smallrye-jwt`)
- `quarkus.http.cors.origins` (ne `quarkus.http.cors=true`)
- `%test.quarkus.http.port=0` (random port); `%dev` datasource na lokální container

## Sdílená infrastruktura (kopíruje se identicky, neduplikovat per-feature)

| Třída | Účel |
|---|---|
| `ApiException(Status, code[, details])` | throwovat místo `Response.status(...)`; `requireOwned(opt, getOwnerId, requesterId)` pro ownership |
| `ApiExceptionMapper` | `@Provider` — mapuje `ApiException` → JSON; žádný per-feature mapper |
| `ValidationExceptionMapper` | `@ServerExceptionMapper` — Bean Validation → `fieldErrors` |
| `ErrorResponse` | jednotný tvar chyby (`code`, `details`, `fieldErrors`); žádný alternativní error tvar |
| `ValidationResult` | response pro `?validate=true`; `ValidationResult.valid()` = prázdný fieldErrors |
| `BaseResource` | abstraktní základ; injektuje `JsonWebToken`, dává `currentUserId()`/`currentUserRole()`; každá resource z něj dědí |
| `DatabaseProducer` | CDI producer `DSLContext` (Postgres dialect) |

## API model binding (response tvary)

Sdílené interface kontrakty — pojmenování řízené rolí operace:

- `*View implements ApiView` — readonly response resource (`UUID id()`)
- `*Data implements ApiData` — write/edit payload
- `*ExtData implements ApiExtData<*Data>` — GET/init pro formulář (wrapper nad `*Data` + readonly kontext)
- `*List/*Page/*Slice implements ApiListOf<T>/ApiPageOf<T>/ApiSliceOf<T,TCursor>` — kolekce / offset stránka / infinite scroll
- cursor pro slice = explicitní record, ne opaque `String`
- `*ExtData` není alternativní write payload ani `*View`; žádný separátní „form API" layer

## Mapping rules (spec element → implementace)

| Spec element | Implementace |
|---|---|
| endpoint | `@Path` třída v `resource/`, jedna na feature, extends `BaseResource` |
| request tělo | POJO/record v `model/` s Bean Validation (`@Valid`, `@NotNull`) |
| response tělo | record v `model/`; citlivá pole (`*_hash`) se neserializují |
| business logika | service v `service/`; resource jen deleguje |
| DB přístup | repository v `repository/` přes jOOQ `DSLContext` |
| validace | Bean Validation na request modelu; server je autorita |
| error | jen kód z `contracts/error-codes.md`; žádný stack trace / interní zpráva |
| response mapping | `static from(<Record> r)` na view recordu — NE `private toResponse()` v service |

## Programming binding (Java realizace `rules/` + `constitution`)

- volitelný návrat v service/repository: `Optional<T>`, ne `null`; `Optional`
  NENÍ default pro request/response fieldy ani jOOQ record fieldy
- pole bez doménové absence → primitiva (`int`, `boolean`, …), ne wrapper
- konečný výčet → enum typ, ne `String` (business logika nevětví nad literály)
- `var` kde je typ z kontextu zřejmý; ne kde by zakryl doménový typ
- query → jOOQ DSL default; raw SQL string = výjimka s důvodem
- netriviální query vstup → explicitní request/filter model, ne dlouhý param list
- **jOOQ `lookupLiteral` vrací `null`** (nethrowuje) — vždy null-check →
  `ApiException(BAD_REQUEST, ...)`; zakázaný vzor: `try { lookupLiteral } catch`

## Testování

- `quarkus-junit5` (`@QuarkusTest`) + REST-assured
- Quarkus DevServices: testy automaticky startují Postgres container + Flyway
- `RestAssured.basePath = "/api/v1"` v **`@BeforeEach`** (ne `@BeforeAll` —
  RESTEasy Reactive resetuje basePath před každým testem → jinak 404)
- DB cleanup v `@BeforeEach` (sdílený `TestHelper.cleanDb(db)`)
- minimální high-signal suite: 1 success / operaci, 1 validace / distinct pravidlo,
  ownership jen kde mění bezpečnostní hranici

### Test anti-patterns (zakázáno generovat)
- POST bez těla s `@Consumes(JSON)` → 415 ne 401; test musí mít `.contentType(JSON)`
- RestAssured deserializuje decimály jako `Float` → `closeTo(double,double)` selže;
  použít float variantu (`equalTo(0.75f)`, `greaterThan/lessThan`)
- `extract().path("field")` musí přesně odpovídat JSON klíči (jinak tiché `null`)

## BCrypt

`BcryptUtil.bcryptHash(password, 12, salt)`, `salt = new byte[16]` přes
`SecureRandom`; verifikace `BcryptUtil.matches(password, hash)`.

## Building blocks — declared

| Knihovna | Role |
|---|---|
| Quarkus (rest, rest-jackson, arc, security) | framework |
| jOOQ | typovaný SQL |
| quarkus-jdbc-postgresql + Flyway | DB + migrace |
| smallrye-jwt (+build) | RS256 JWT |
| hibernate-validator | Bean Validation |
| elytron-security-common | BCrypt |
| junit5 + rest-assured | testy |

## Scaffold

Reálná kostra: `templates/scaffolds/java-quarkus/` — Watson ji kopíruje a
přejmenuje `com.example.app` → `<base-package>` projektu. Kanonické patterny
výše jsou v kostře instancované (shared infra + 1 ukázkový vertical slice).
Ted: stack-defined patterny = `scaffold-only` default.

## Extraction Candidates

| Pattern | Výskyty | Soubory |
|---|---|---|
| _(prázdné — Ted plní po každé wave)_ | | |

## Pozn. pro Watson

- Obsah od `## Technologie` po `## Extraction Candidates` se kopíruje do
  projektového `stack/server.md`; `<base-package>` nahraď balíčkem projektu.
- Postgres je integrální (jOOQ codegen) — `_db/postgres` fragment NEpřidávat.
- Po seedu zkopíruj kostru `scaffolds/java-quarkus/` do `server/` a přejmenuj package.
