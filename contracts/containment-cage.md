---
feature-id: containment-cage
type: contract
---
# Kontrakt — containment-cage (klec ↔ appka rozhraní)

Technický kontrakt definující rozhraní mezi bezpečnostní klecí a workspace aplikací.

## Overlay-at-deploy model

Cage-deploy build ignoruje `Dockerfile.workspace` z repo appky a nahradí ho hardened verzí
z `dream-team-sandbox`. Repo appky není modifikováno.

## Síťový kontrakt

- Workspace komunikuje ven výhradně přes `$http_proxy=http://127.0.0.1:4750` (env injektnutý entrypointem klece).
- Proxy je jediná brána doménové granularity.
- Host-enforced politika povoluje :443 pouze na proxy CIDR a approved CIDR (privátní síť); přímé spojení blokováno.
- DNS: pouze allowlisted resolver; přímý UDP :53 jinam blokován.
- Metadata endpoint `169.254.0.0/16` blackhole.

## Izolace app ↔ AI

- Dvě oddělené microVM (`dream-team-app` a `dream-team-workspace`), dva kernely.
- Žádný sdílený volume ani sdílená síťová namespace.
- Komunikace mezi nimi výhradně přes privátní síť (6PN nebo ekvivalent na jiném substrátu).

## Secrets hranice

Tyto secrets nesmí být přítomny ve workspace env ani volume:

| Secret | Umístění |
|---|---|
| `CLOUDFLARE_TUNNEL_TOKEN` | app machine only |
| `CF_ACCESS_AUD` | app machine only |
| `GH_TOKEN` | app machine only |
| `ADMIN_BOOTSTRAP_TOKEN` | app machine only |

## Git credential scope

- Workspace dostane deploy key nebo fine-grained PAT scoped na jedno cílové repo.
- Token/key nesmí mít write oprávnění k jiným repozitářům.

## Přenositelnost substrátu

Fly Network Policy applier a egress proxy ACL musí být přenositelné na VPS
(nftables na hypervisor hostu) bez přepisu logiky klece.
