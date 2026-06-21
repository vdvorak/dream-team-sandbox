"""Host-enforced policy enforcer adapter (substrát-agnostický, CE-9).

Vrstva 2 je JEDINÝ nositel egress garance (CE-1) a JEDINÝ bod, kde se mění enforcer
při změně substrátu (contracts §3). Tady žije abstrakce `ruleset → enforcer-specific call`.

- `EnforcerAdapter` — abstraktní rozhraní. Vstup = abstraktní ruleset H1–H7 (ruleset.py).
- `FlyNetworkPolicyAdapter` — dnešní substrát (Fly Network Policy control-plane API).
- (později) `NftablesHostAdapter` — VPS substrát (nftables na hypervisor hostu).

EXTRACTION CANDIDATE (stack §Extraction Candidates): při přidání VPS enforceru se tento
modul extrahuje do sdíleného balíku s ruleset abstrakcí. Dnes feature-local (1 substrát).

Fail-closed (CE-2): apply selže → PolicyApplyFailedError → cage-deploy ABORT. Žádný
"best-effort" — bez aktivní policy se workspace machine NESPUSTÍ (I1).
"""

from __future__ import annotations

import abc
from dataclasses import dataclass
from typing import Any, Callable

from server.cage.errors import NoPolicyError, PolicyApplyFailedError
from server.cage.policy.ruleset import Action, Rule, assert_complete


class EnforcerAdapter(abc.ABC):
    """Abstraktní adaptér vrstvy 2. Jediný měněný bod mezi Fly a VPS (CE-9)."""

    #: lidsky čitelné jméno substrátu (do deploy logu)
    substrate: str = "abstract"

    @abc.abstractmethod
    def render(self, ruleset: list[Rule]) -> Any:
        """ruleset H1–H7 → enforcer-specific reprezentace (payload/ruleset text)."""

    @abc.abstractmethod
    def apply(self, ruleset: list[Rule]) -> None:
        """Aplikuje ruleset na host enforcer. Fail-closed: selže → PolicyApplyFailedError."""

    def validate_and_apply(self, ruleset: list[Rule]) -> None:
        """Společná fail-closed obálka pro všechny adaptéry.

        WHY (CE-2): nejdřív ověř kompletnost rulesetu (NoPolicyError), pak teprve apply.
        Nikdy neaplikuj neúplnou politiku — to by mohlo vynechat default-deny (I1).
        """
        assert_complete(ruleset)  # → NoPolicyError při neúplnosti
        self.apply(ruleset)


# --- Fly.io substrát (dnešní enforcer) ----------------------------------------

# TODO-spike(heimdall): potvrdit tvar Fly Network Policy API (contracts §7) —
# zejm. že podporuje per-port/CIDR egress rules H1–H7 a default-deny. Endpoint cesta
# je dle contracts §3; reálný tvar payloadu potvrdí heimdall spike.
FLY_NETWORK_POLICY_ENDPOINT = "/v1/apps/{app}/network_policies"


@dataclass
class FlyNetworkPolicyAdapter(EnforcerAdapter):
    """Fly Network Policy control-plane API adaptér (contracts §3).

    `http_post` je injektnutelný callable (url, json_body, headers) -> (status, body),
    aby šla apply logika testovat bez reálné sítě a aby fail-closed větve byly pokryté
    unit testy. V provozu se dosadí reálný HTTP klient (requests / fly API SDK).
    """

    app: str = "dream-team-workspace"
    api_token: str = ""
    http_post: Callable[[str, dict, dict], tuple[int, str]] | None = None
    substrate: str = "fly"

    def render(self, ruleset: list[Rule]) -> dict:
        """ruleset H1–H7 → Fly Network Policy JSON payload.

        Pořadí pravidel = priorita (zachováno z ruleset.py). `priority` index drží
        sémantiku ALLOW před default-deny — jinak by H6 (deny *) přebil H1–H3.
        """
        rules_payload = []
        for prio, r in enumerate(ruleset):
            rules_payload.append(
                {
                    "id": r.id,
                    "priority": prio,
                    "direction": r.direction.value,
                    "protocol": r.protocol,
                    "destination": r.target,
                    "action": r.action.value,
                    "invariant": r.invariant,  # audit anotace
                }
            )
        return {
            "app": self.app,
            "default_action": Action.DENY.value,  # default-deny posture (CE-1)
            "rules": rules_payload,
        }

    def apply(self, ruleset: list[Rule]) -> None:
        """Apply přes Fly API. Fail-closed: nenastavený transport / non-2xx → ABORT."""
        if self.http_post is None:
            # WHY (CE-2): bez transportu nelze policy aplikovat ANI ověřit → ABORT.
            raise PolicyApplyFailedError(
                "Fly API transport není nakonfigurován (http_post=None) — "
                "nelze aplikovat host policy, fail-closed ABORT"
            )
        payload = self.render(ruleset)
        url = FLY_NETWORK_POLICY_ENDPOINT.format(app=self.app)
        headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json",
        }
        try:
            status, body = self.http_post(url, payload, headers)
        except Exception as exc:  # transport selhal → fail-closed
            raise PolicyApplyFailedError(
                f"Fly Network Policy API volání selhalo: {exc}"
            ) from exc
        if not (200 <= status < 300):
            raise PolicyApplyFailedError(
                f"Fly Network Policy API vrátilo {status}: {body}"
            )


def get_enforcer(substrate: str, **kwargs: Any) -> EnforcerAdapter:
    """Factory: vrátí adaptér dle substrátu. Neznámý substrát → fail-closed.

    WHY (CE-2/CE-9): neznámý enforcer = nelze garantovat egress → NoPolicyError,
    NE tichý fallback na "žádná policy".
    """
    if substrate == "fly":
        return FlyNetworkPolicyAdapter(**kwargs)
    # VPS nftables adaptér = budoucí (stack §Extraction Candidates). Dnes není → ABORT.
    raise NoPolicyError(
        f"neznámý/neimplementovaný enforcer substrát '{substrate}' — "
        "nelze aplikovat host policy (fail-closed). Podporováno: 'fly'."
    )
