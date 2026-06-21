"""Pre-deploy lint/scan — fail-closed deploy guards (contracts §4, §6 krok 5).

Tři regrese-guardy, které MUSÍ FAILnout deploy (ne varovat):
  - [http_service] leak v overlay fly.workspace.toml → ERR_INGRESS_LEAK (I7, CE-8/FP-1)
  - high-value secret v workspace env/volume        → ERR_SECRET_LEAK (I9)
  - git write credential ve workspace               → ERR_GIT_WRITE_CRED (I10, CE-7)

Vše fail-closed (CE-2): nález = deploy ABORT před spuštěním machine.
"""

from __future__ import annotations

import re
from pathlib import Path

from server.cage.errors import GitWriteCredError, IngressLeakError, SecretLeakError

# High-value secrets, které NIKDY nesmí být ve workspace env/volume (I9, contracts §3).
HIGH_VALUE_SECRETS: tuple[str, ...] = (
    "CLOUDFLARE_TUNNEL_TOKEN",
    "CF_ACCESS_AUD",
    "GH_TOKEN",
    "ADMIN_BOOTSTRAP_TOKEN",
)

# Git write credential indikátory (CE-7: workspace NIKDY nedostane git write).
# Pozn.: read-only/scoped clone token je OK; tyto vzory cílí na write/PAT/SSH-key (I10).
GIT_WRITE_CRED_PATTERNS: tuple[re.Pattern, ...] = (
    re.compile(r"github_pat_[A-Za-z0-9_]+"),  # fine-grained PAT
    re.compile(r"ghp_[A-Za-z0-9]{20,}"),  # classic PAT
    re.compile(r"ghs_[A-Za-z0-9]{20,}"),  # app/server token
    re.compile(r"-----BEGIN (?:OPENSSH|RSA|EC) PRIVATE KEY-----"),  # deploy/SSH write key
    re.compile(r"GIT_WRITE_TOKEN", re.IGNORECASE),
    re.compile(r"GH_WRITE_TOKEN", re.IGNORECASE),
)

# Regex pro [http_service] (i s mezerami / pod komentářem to detekuje řádek, který
# NENÍ zakomentovaný). WHY (CE-8): jen aktivní (nezakomentovaná) sekce obchází policy.
_HTTP_SERVICE_RE = re.compile(r"^\s*\[\[?http_service\]?\]", re.MULTILINE)


def lint_no_http_service(fly_config_text: str) -> None:
    """FAIL deploy, pokud overlay fly config obsahuje aktivní [http_service] (I7).

    Komentované řádky (`# [http_service]`) se ignorují — počítá jen aktivní sekce.
    """
    for m in _HTTP_SERVICE_RE.finditer(fly_config_text):
        # Ověř, že řádek není zakomentovaný (komentář před '[').
        line_start = fly_config_text.rfind("\n", 0, m.start()) + 1
        prefix = fly_config_text[line_start : m.start()]
        if "#" not in prefix:
            raise IngressLeakError(
                "overlay fly.workspace.toml obsahuje aktivní [http_service] — "
                "fly-proxy ingress obchází host-enforced policy (I7/CE-8/FP-1)"
            )


def scan_secret_leak(env: dict[str, str]) -> None:
    """FAIL deploy, pokud high-value secret je ve workspace env (I9)."""
    leaked = sorted(k for k in env if k in HIGH_VALUE_SECRETS)
    if leaked:
        raise SecretLeakError(
            f"high-value secret(y) ve workspace env: {', '.join(leaked)} — "
            "tyto patří jen na app machine (I9)"
        )


def scan_git_write_cred(*texts: str) -> None:
    """FAIL deploy, pokud nějaký text obsahuje git write credential (I10/CE-7).

    Skenuje libovolné textové zdroje (env hodnoty, volume soubory předané jako string).
    """
    blob = "\n".join(texts)
    for pat in GIT_WRITE_CRED_PATTERNS:
        if pat.search(blob):
            raise GitWriteCredError(
                "git write credential nalezen ve workspace kontextu — "
                "workspace NIKDY nedostane git write (CE-7/I10). "
                f"vzor: {pat.pattern}"
            )


def lint_overlay_fly_config(path: str | Path) -> None:
    """Načte overlay fly config a spustí [http_service] lint (fail-closed)."""
    text = Path(path).read_text(encoding="utf-8")
    lint_no_http_service(text)
