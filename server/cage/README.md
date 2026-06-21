# cage — containment-cage implementace (server/deploy)

Implementace bezpečnostní klece dle `contracts/containment-cage.md`, `rules/cage-enforcement.md`
a `PROJECT-CONSTITUTION.md` (invarianty I1–I11). Vše **fail-closed** (CE-2).

> Opacita (CE-4/I11): tyto artefakty žijí JEN v `dream-team-sandbox`. Do repa appky se nikdy
> nezapíšou. Overlay-at-deploy je read-only čte appkové soubory, výstup je workspace image.

## Layout

```
server/cage/
├── errors.py                       # error-code registry (1:1 contracts/error-codes.md)
├── policy/
│   ├── ruleset.py                  # abstraktní ruleset H1–H7 (substrát-agnostický, CE-9)
│   ├── enforcer.py                 # enforcer adapter (Fly dnes; VPS nftables = extraction candidate)
│   └── acl.py                      # Smokescreen ACL render (CF doména z env, rozhodnutí (d))
├── deploy/
│   ├── drift.py                    # WORKSPACE_DEF_HASH drift-detekce (CE-6)
│   ├── lint.py                     # pre-deploy guardy: [http_service]/secret/git-write (I7/I9/I10)
│   └── cage_deploy.py              # orchestrace — jediná legitimní deploy cesta (CE-5)
├── overlay/                        # hardened overlay artefakty (přeloží přes appku při deploy)
│   ├── Dockerfile.workspace        # non-root, Smokescreen, nftables, capsh (NAHRAZUJE appkový)
│   ├── entrypoint.sh               # de-root sekvence kroky 0–4 (CE-3, ZÁVAZNÉ pořadí)
│   ├── nftables.cage.conf          # vrstva 3 default-DROP (defense-in-depth)
│   ├── fly.workspace.toml          # 6PN-only, BEZ [http_service] (I7)
│   └── smokescreen-acl.rendered.yaml  # (gitignored) render-time artefakt, generuje cage-deploy
└── cage-deploy.lock                # (generováno) pinned WORKSPACE_DEF_HASH
```

## Jazyk / runtime

- **Python 3.12** pro logickou vrstvu (ruleset, enforcer adapter, ACL render, drift, lint,
  orchestrace) — testovatelnost (pytest dostupný, bats ne), snadné pokrytí fail-closed větví,
  substrát-portabilita (CE-9).
- **POSIX sh** pro `overlay/entrypoint.sh` — MUSÍ to být container init běžící jako root
  (de-root sekvence). Shell je tady nutnost, ne volba.

## Deploy (operátor)

```sh
export CF_ACCESS_TEAM_DOMAIN=<team-label>     # rozhodnutí (d): CF doména z env, nehardcoduje se
PYTHONPATH=. python3 -m server.cage.deploy.cage_deploy --app-repo /path/to/dream-team-app
# při legitimní změně appkové workspace definice (po re-review overlay):
#   ... cage_deploy --accept-drift
```

Cage-deploy je **jediná** legitimní deploy cesta workspace (CE-5). Přímý `fly deploy` workspace
je provozně zakázán. Bez aktivní host policy se deploy NEDOKONČÍ (I1).

## Testy

```sh
python3 -m pytest tests/server/unit/ -q
```

Pokrývají: ruleset H1–H7 tvar/pořadí/kompletnost, ACL templating + injection guard, drift
match/mismatch/re-pin, enforcer fail-closed apply, pre-deploy lint guardy, orchestrace
fail-closed sekvence (policy PŘED deploy), error-code registry.
