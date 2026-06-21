"""Drift-detekce overlay vs. appkové workspace definice (CE-6, contracts §2).

Cage-deploy je JEDINÁ legitimní deploy cesta. Overlay (hardened Dockerfile/entrypoint)
sedí na konkrétní podobě appkových souborů. Když se ty změní, overlay nemusí sedět →
deploy FAIL `ERR_CAGE_DRIFT` + viditelné upozornění; operátor vědomě re-pinuje `--accept-drift`.

WORKSPACE_DEF_HASH = sha256 nad sadou appkových souborů, na které overlay sedí
(contracts §2): Dockerfile.workspace (base vrstva) ∪ agent.py ∪ managed-settings.json
∪ deny-secrets.sh ∪ fly.workspace.toml.

Fail-closed (CE-2/CE-6): neshoda bez explicitního re-pinu → deploy NEDOKONČEN. ŽÁDNÝ tichý sync.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from server.cage.errors import CageDriftError

# Příponová cesta každé appkové komponenty workspace definice (relativně k repu appky).
# Pořadí je STABILNÍ (hash závisí na pořadí) — nepřeskupovat bez re-pinu.
WORKSPACE_DEF_FILES: tuple[str, ...] = (
    "Dockerfile.workspace",
    "poc/workspace-container/agent.py",
    "poc/workspace-container/managed-settings.json",
    "poc/workspace-container/deny-secrets.sh",
    "fly.workspace.toml",
)

LOCK_HEADER = "# cage-deploy.lock — pinned WORKSPACE_DEF_HASH (CE-6). NEeditovat ručně.\n"
LOCK_KEY = "WORKSPACE_DEF_HASH"


def compute_workspace_def_hash(app_repo: str | Path) -> str:
    """Spočítá WORKSPACE_DEF_HASH z aktuálních appkových souborů (read-only).

    Hash je deterministický: pro každý soubor přimícháme jeho relativní cestu (oddělí
    obsahy, kdyby se shodovaly) a pak obsah. Chybějící soubor → fail-closed (drift FAIL).
    """
    app_repo = Path(app_repo)
    h = hashlib.sha256()
    for rel in WORKSPACE_DEF_FILES:
        p = app_repo / rel
        if not p.is_file():
            # WHY (CE-2): chybí komponenta definice → overlay nemůže spolehlivě sednout.
            raise CageDriftError(
                f"appkový soubor workspace definice chybí: {rel} (v {app_repo}) — "
                "nelze ověřit drift, fail-closed"
            )
        h.update(rel.encode("utf-8"))
        h.update(b"\0")
        h.update(p.read_bytes())
        h.update(b"\0")
    return h.hexdigest()


def read_pinned_hash(lock_path: str | Path) -> str | None:
    """Přečte pinned hash z cage-deploy.lock. None = ještě nikdy nepinnováno."""
    lock_path = Path(lock_path)
    if not lock_path.is_file():
        return None
    for line in lock_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith(f"{LOCK_KEY}="):
            return line.split("=", 1)[1].strip()
    return None


def write_pinned_hash(lock_path: str | Path, value: str) -> None:
    """Zapíše/re-pinne WORKSPACE_DEF_HASH do cage-deploy.lock (vědomý re-pin)."""
    lock_path = Path(lock_path)
    lock_path.write_text(f"{LOCK_HEADER}{LOCK_KEY}={value}\n", encoding="utf-8")


def check_drift(
    app_repo: str | Path,
    lock_path: str | Path,
    accept_drift: bool = False,
) -> str:
    """Ověří drift; vrátí aktuální hash. Fail-closed dle CE-6.

    Pravidla:
      - lock neexistuje (první deploy) → napíše pin, vrátí hash (žádný drift).
      - aktuální hash == pinned → OK, vrátí hash.
      - aktuální hash != pinned + `accept_drift=False` → CageDriftError (deploy FAIL).
      - aktuální hash != pinned + `accept_drift=True` → vědomý re-pin, vrátí nový hash.
    """
    current = compute_workspace_def_hash(app_repo)
    pinned = read_pinned_hash(lock_path)

    if pinned is None:
        # První cage-deploy: pin aktuální definici (žádný drift k detekci).
        write_pinned_hash(lock_path, current)
        return current

    if current == pinned:
        return current

    if not accept_drift:
        # WHY (CE-6/I11): tichý sync zakázán. Operátor musí vědomě re-pinovat.
        raise CageDriftError(
            "Workspace image definice appky se změnila od posledního cage-deploy (drift) — "
            "overlay nemusí sedět. Re-review overlay vůči nové definici, pak spusť "
            f"s `--accept-drift` (re-pin hash). pinned={pinned[:12]}… current={current[:12]}…"
        )

    # Vědomý re-pin (--accept-drift): operátor potvrdil, že overlay byl re-reviewován.
    write_pinned_hash(lock_path, current)
    return current
