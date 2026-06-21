# Scaffold — Java + Quarkus + jOOQ + PostgreSQL

Reálná spustitelná kostra serveru. Watson ji při setupu java-quarkus projektu
**zkopíruje** do `server/` a přejmenuje placeholder identifikátory na projektové.
Kanonický popis patternů: `templates/stacks/_base/java-quarkus.md`.

## Co Watson nahradí při kopii

- package `com.example.app` → `<base-package>` projektu (rekurzivně v `src/**`
  i v `build.gradle` jOOQ `target.packageName`)
- `rootProject.name = 'app-server'` v `settings.gradle`
- DB/identifikátory `app` v `run.sh` + `application.properties` dle projektu

(Mechanika: `git grep -l com.example.app | xargs sed -i 's/com.example.app/<pkg>/g'`
+ přesun adresářů `src/main/java/com/example/app` → balíčková cesta projektu.)

## Layout (zrcadlí projekt)

```
server/                      # → kopíruje se do projektového server/
  build.gradle  settings.gradle  gradle.properties  run.sh
  src/main/java/com/example/app/{shared,example,DatabaseProducer}
  src/main/resources/{application.properties,dev/}
  src/test/java/com/example/app/example/
contracts/db/migrations/     # → kopíruje se do projektového contracts/ (Chandler-owned)
  V1__init.sql
```

`server/build.gradle` referencuje `../contracts/db/migrations` — funguje
standalone (tady) i po vložení (server/ + contracts/ jako siblings v projektu).

## Co kostra obsahuje

- **server/.../shared/** — kanonická cross-cutting infra (ApiException + mappery,
  BaseResource, ErrorResponse, ValidationResult, Api* binding interfaces).
  Kopíruje se identicky do každého projektu — **neduplikovat per-feature.**
- **server/.../example/** — JEDEN ukázkový vertical slice (resource → service →
  repository → model) ukazující kanonický tvar včetně jOOQ a `View.from(record)`.
- **server/build.gradle** s jOOQ codegen pipeline, **application.properties**,
  **contracts/db/migrations/V1__init.sql** (ukázková tabulka pro codegen).

## Prerekvizity buildu (honest)

1. **Docker** — jOOQ generuje třídy přes TestContainers Postgres; testy běží
   přes Quarkus DevServices (Postgres container). Bez Dockeru build neproběhne.
2. **Dev RS256 klíče** — viz `server/src/main/resources/dev/README.md` (vygeneruj
   `privateKey.pem` + `publicKey.pem`; do repa smí jen dev klíče).
3. **Gradle wrapper** — kostra ho neveze (binární `gradle-wrapper.jar`).
   Po kopii: `cd server && gradle wrapper` vygeneruje `gradlew`.

## Build & run

```bash
cd server
gradle wrapper            # jednou — vygeneruje gradlew (pak používej ./gradlew)
./gradlew build          # spustí concatMigrations → generateJooq → compile → test
bash run.sh              # dev: nastartuje Postgres container + quarkusDev
```

První feature: zkopíruj `example/` jako vzor, přidej migraci do
`contracts/db/migrations/`, jOOQ vygeneruje record, drž se mapping rules
ze `stack/server.md`.

## Docker dev-run (model pro Javu)

`docker_dev: true` znamená u Javy **DB v kontejneru + app přes gradle dev** (jak dělá
`run.sh`: nastartuje `postgres:16` container, pak `./gradlew quarkusDev`). Plný
app-in-container se zde **nezavádí** záměrně: jOOQ codegen běží přes TestContainers
(potřebuje docker socket) a gradle wrapper se ve scaffoldu nevozí — kombinace dělá
z app-in-container křehkost bez zisku. Host-nezávislost se drží na úrovni DB + JDK.
