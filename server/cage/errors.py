"""Error code registry — containment-cage (Python mirror of contracts/error-codes.md).

JEDINÝ zdroj pravdy pro error kódy v Python vrstvě klece (host-policy applier +
cage-deploy obálka). Každý kód je fail-closed (CE-2): jeho vznik znamená
"enforcement nelze aplikovat/ověřit" → deploy NEDOKONČEN, NIKDY best-effort fallback.

Kódy a triggery MUSÍ 1:1 odpovídat contracts/error-codes.md. Když se registr změní,
změna jde nejdřív do kontraktu (vlastní ted-architect), pak sem.
"""

from __future__ import annotations


class CageError(Exception):
    """Bázová třída všech klec-error situací. Nese strojový `code` z registru.

    WHY: fail-closed (CE-2). Deploy obálka chytá CageError, vytiskne kód + důvod
    a ABORTuje s nenulovým exit. Nikdy se nepokračuje "best-effort".
    """

    code: str = "ERR_CAGE_UNKNOWN"

    def __init__(self, detail: str = "") -> None:
        self.detail = detail
        msg = self.code if not detail else f"{self.code}: {detail}"
        super().__init__(msg)


# --- deploy / vrstva 2 (host-enforced policy) ---


class NoPolicyError(CageError):
    """Chybí kompletní ruleset H1–H7 před spuštěním machine. → deploy ABORT (I1)."""

    code = "ERR_NO_POLICY"


class PolicyApplyFailedError(CageError):
    """Host-enforced policy API selhalo při apply. → deploy ABORT (I1)."""

    code = "ERR_POLICY_APPLY_FAILED"


# --- deploy / overlay ---


class CageDriftError(CageError):
    """WORKSPACE_DEF_HASH neshoda od posledního cage-deploy.

    → deploy FAIL + upozornění; vyžaduje `--accept-drift` re-pin (CE-6, I11).
    """

    code = "ERR_CAGE_DRIFT"


# --- runtime / vrstva 1 (egress proxy) ---


class ProxyDownError(CageError):
    """Smokescreen sidecar nedostupný. → fail-CLOSED (žádný egress), observability (I2)."""

    code = "ERR_PROXY_DOWN"


# --- runtime / de-root (vznikají v entrypoint.sh; zde pro testovatelnost cest) ---


class InvmFwFailedError(CageError):
    """In-VM nftables instalace selhala (entrypoint krok 1). → entrypoint ABORT (I4)."""

    code = "ERR_INVM_FW_FAILED"


class CapDropFailedError(CageError):
    """Drop CAP_NET_ADMIN z bounding setu selhal (krok 2). → entrypoint ABORT (I4)."""

    code = "ERR_CAP_DROP_FAILED"


class NnpFailedError(CageError):
    """no_new_privs=1 se nepodařilo nastavit (krok 3). → entrypoint ABORT (I6)."""

    code = "ERR_NNP_FAILED"


# --- deploy / overlay lint + pre-scan ---


class IngressLeakError(CageError):
    """[http_service] nalezen v overlay fly.workspace.toml. → deploy ABORT (I7)."""

    code = "ERR_INGRESS_LEAK"


class SecretLeakError(CageError):
    """High-value secret v workspace env/volume. → deploy ABORT (I9)."""

    code = "ERR_SECRET_LEAK"


class GitWriteCredError(CageError):
    """Git write credential nalezen ve workspace (regrese rozhodnutí (b)). → deploy ABORT (I10)."""

    code = "ERR_GIT_WRITE_CRED"


# --- post-deploy smoke ---


class LoginPersistError(CageError):
    """Claude login token se neuložil/nepřežil restart po de-root. → smoke FAIL (regrese-guard §1)."""

    code = "ERR_LOGIN_PERSIST"


# Registr pro introspekci/testy: code -> třída. Drží se contracts/error-codes.md.
ERROR_CODES: dict[str, type[CageError]] = {
    cls.code: cls
    for cls in (
        NoPolicyError,
        PolicyApplyFailedError,
        CageDriftError,
        ProxyDownError,
        InvmFwFailedError,
        CapDropFailedError,
        NnpFailedError,
        IngressLeakError,
        SecretLeakError,
        GitWriteCredError,
        LoginPersistError,
    )
}
