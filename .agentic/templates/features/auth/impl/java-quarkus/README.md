# auth impl — java-quarkus (credentials `base`)

Reference implementation of the `auth` feature `base` variant (spec: `../../spec.md`) for Quarkus.

> ⚠️ **BUILD-VERIFICATION PENDING.** Tahle impl je **strukturálně kompletní, ale NEbyla
> zkompilována ani otestována** (psána bez gradle/jOOQ codegen/Docker env). Auth je
> security-critical → **NENASazuj** bez `./gradlew build` + `QuarkusTest`. Audit-once (Heimdall)
> proběhne až po build-verifikaci. Python-fastapi impl je ověřená (pytest 8/8 oba strategie) — ber ji
> jako kontraktní referenci chování.

## Stack idiomy
- **bcrypt** přes `BcryptUtil` (quarkus-elytron-security-common) — `security/Passwords.java`
- **JWT** přes SmallRye build (`io.smallrye.jwt.build.Jwt`); `/me` chráněno `@Authenticated`
  (quarkus-smallrye-jwt ověří proti dev klíčům). Issuer se bere z `mp.jwt.verify.issuer` (config).
- **session** = `app_session` tabulka + httpOnly cookie + jOOQ lookup; `SecureRandom` token.
- **jOOQ** codegen z `contracts/db/migrations/V2__auth.sql` (+ `V3__sessions.sql` pro session)
  → `AppUserRecord`, `APP_USER`, `APP_SESSION`. **Spusť jOOQ codegen před kompilací.**

## Structure: common + chosen strategy
```
auth/model/{RegisterData,LoginData,UserView,TokenView}.java   COMMON (+TokenView jen jwt)
auth/repository/AuthRepository.java                            COMMON
auth/service/AuthService.java                                  COMMON
auth/security/Passwords.java                                   COMMON
auth/resource/AuthResourceJwt.java                            ← token_strategy=jwt
auth/resource/AuthResourceSession.java + repository/SessionRepository.java
                                       + V3__sessions.sql      ← token_strategy=session
contracts/db/migrations/V2__auth.sql                           (user — oba)
```

## Overlay
Kopíruj common + soubory zvolené strategie do `server/src/main/java/com/example/app/auth/`
+ migrace do `contracts/db/migrations/`. JAX-RS resource se registruje sám (`@Path`); žádný
wiring v main netřeba (na rozdíl od python). Endpoints + chování viz spec / python README.

## Build-verification TODO (než ready)
- [ ] jOOQ codegen + `./gradlew build` (kompilace) zelená
- [ ] `QuarkusTest` (register/login/me, no-enumeration, duplicate, logout) — mirror python testů
- [ ] ověřit `mp.jwt.verify.issuer` == issuer v loginu; dev RS256 klíče přítomné
- [ ] Heimdall audit → pak `feature.yaml` java-quarkus = ready
