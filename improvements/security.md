---
feature-id: runtime-control-plane
type: improvements
source: heimdall-security (wave 2026-06-21-runtime-lifecycle, security gate PASS)
---
# Security advisory — runtime control-plane (slice 2 hardening)

Bezpečnostní audit slice 1 = **PASS** (žádný blocking). Tyto advisory nálezy nejsou
blokující pro slice 1, ale MUSÍ být vyřešeny ve slice 2, až přijde reálný enforcement
(CageEnforcementProvider) + mTLS dle kontraktu §3.

## A1 — dev service_token bez production fail-fast guardu
`server/runtime/config.py` — default `service_token = "dev-token-change-me-in-production"`
je honestně self-labeling jako non-prod a přepsatelný přes `SERVICE_TOKEN` env, ALE nic
nezabrání bootu reálného nasazení s nezměněným dev tokenem.
**Slice 2:** fail-fast při startu, pokud `enforcement_provider == cage` A `service_token`
je stále dev default → odmítnout nastartovat reálný enforcement provider se známým tokenem.
returns_to: backend (slice 2).

## A2 — token compare není constant-time
`server/runtime/router.py` — fallback service token se porovnává `!=` (ne constant-time).
Teoretický timing side-channel (low severity: service-to-service, jediný token, dev fallback).
**Slice 2:** `hmac.compare_digest` až při hardeningu reálné auth cesty.
returns_to: backend (slice 2).
