# Scaffold — Flutter mobile (iOS + Android)

Reálná spustitelná kostra mobilního klienta z jedné Dart kódové báze. Watson ji při
setupu flutter projektu **zkopíruje** do `clients/mobile/`. Kanonické knihovny:
`templates/stacks/recommended-libs.yaml` (`flutter`).

## Stack (vetted)

| Vrstva | Volba | Proč |
|---|---|---|
| stav | **flutter_riverpod** (`AsyncNotifier`) | typovaný async stav, testovatelný, DI |
| routing | **go_router** | deklarativní, deep-link ready |
| HTTP | **dio** | interceptory (chyby → `ApiError`) |
| modely | **plain immutable Dart** | turnkey build bez codegenu; freezed je optional capability |
| i18n | **gen-l10n** (`intl` + ARB) | i18n od prvního řádku (constitution); žádné hardcoded texty |
| testy | **flutter_test + mocktail** | mock bez codegenu |

## Co kostra ukazuje

- **shared/** — kanonická infra: `api_client` (dio + interceptor) mapuje chybu API
  na `ApiError` tvaru **`{code, details}`** (identicky s python/java backendem);
  `form_model` = centrální write binding (rules/frontend.md §Form model — jeden
  model = pravda o data/errors/touched/submitting/dirty; validace = dry-run; tenká
  `FormFieldBinding`; `submit` dělá validation-only → commit).
- **example/** — JEDEN vertical slice v kanonickém tvaru:
  `model → repository → controller (Riverpod) → page`. UI jen renderuje `AsyncValue`.

## Layout

```
flutter/
  pubspec.yaml  analysis_options.yaml  l10n.yaml  .gitignore
  l10n/{app_en,app_cs}.arb              # zdroj překladů (gen-l10n)
  lib/main.dart                         # ProviderScope + App
  lib/src/app.dart  router.dart
  lib/src/shared/{api_client,api_error}.dart
  lib/src/example/{example_model,example_repository,example_controller,example_page}.dart
  test/example_repository_test.dart
```

## Build & test

```bash
cd clients/mobile        # po kopii Watsonem; ve scaffoldu jsi přímo zde
flutter pub get          # stáhne deps + spustí gen-l10n (generate: true)
flutter analyze          # statická analýza (flutter_lints)
flutter test             # unit testy (bez emulátoru — čistá logika/repo)
flutter run              # na připojeném zařízení/emulátoru (iOS/Android)
```

> **Platform složky** (`ios/`, `android/`) zde nejsou — generuje je `flutter create .`
> nad touto kostrou (drží je flutter SDK, ne scaffold). Po kopii spusť jednou:
> `flutter create --platforms=ios,android .`

## Co Watson/projekt upraví

- `pubspec.yaml` `name` + `description` → projekt.
- `lib/src/shared/api_client.dart` `API_BASE_URL` (dart-define) → adresa backendu.
- `l10n/*.arb` → texty projektu; přidej locale = přidej `app_<locale>.arb`.

První feature: zkopíruj `example/` jako vzor (model→repo→controller→page), texty do ARB.

## Docker dev-run

`docker_dev: false` — Flutter SDK + emulátor/zařízení běží na hostu (GUI toolchain
se v kontejneru nevyplatí). Backend, na který klient míří, běží v Dockeru (jeho scaffold).
