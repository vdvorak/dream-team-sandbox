---
feature-id: runtime-control-plane
type: improvements
source: vitek-quality (wave 2026-06-21-runtime-lifecycle, code-quality gate PASS) + sheldon-spec (W3)
---
# Code-quality & contract advisory — runtime control-plane (slice 2)

Code-quality audit slice 1 = **PASS** (jen advisory, žádný blocking). Drobné vylepšení
na slice 2 / kdykoli:

## A1 — chybějící type anotace (main.py)
`server/runtime/main.py` — `create_runtime_app(enforcement_provider_override=None)` a
`_build_provider(settings)` bez type anotací. Doplnit `EnforcementProvider | None` resp.
`(settings: RuntimeSettings) -> EnforcementProvider`. Explicitní DI boundary.

## A2 — duplikovaný test-helper `check_keys` (4× kopie)
Rekurzivní grep-value helper je 4× (test_runtime_lifecycle_integration.py:1083,1105;
test_runtime_lifecycle.py:643; inline grep_strings:522). Extrahovat do `tests/conftest.py`
nebo `tests/helpers.py`. Nový extraction candidate.

## A3 — WHAT-flavoured komentář
`server/runtime/service.py:154` — komentář u wake/provisioning popisuje WHAT místo WHY.

## A4 — status/phase holé `str` místo `Literal`
`models.py:71,82`, `repository.py:29` — `EnvironmentRecord.status` (dataclass, bez Pydantic
validace) by měl být `Literal[...]` → zachytí překlep při assignmentu.

## A5 — prázdný auth.py placeholder
`server/runtime/auth.py` — 3řádkový placeholder bez importu. Smazat a přidat až při mTLS slice,
nebo `__all__ = []` + datum.

## W3 (contract, source: spec-audit) — healthz 503 chybí v OpenAPI responses
`contracts/api/runtime.openapi.yaml` — `GET /v1/healthz` definuje jen `200`, ale spec
§Edge cases + AC-9c + rules RCP-A3 počítají s `503` (provider nedostupný). Slice 1 kód
`503` reálně vrací. Pre-existing gap (mimo záměrnou deltu). **Slice 2:** doplnit `503`
response (ref RuntimeUnavailable) do healthz v OpenAPI — non-breaking.
