"""LifecycleService — state machine, fail-closed logic, per-project-id serialization (RCP-A1).

This is the only layer that:
  - Runs the state machine (none→provisioning→ready→asleep/destroyed).
  - Holds asyncio.Lock per project_id (serializes concurrent ensure for same id, RCP-1d).
  - Calls EnforcementProvider (RCP-A2).
  - Translates EnforcementFailed.kind → app-facing error code (RCP-A5, NEVER by internal_code).
  - Validates tool against allowlist → 400 ERR_TOOL_NOT_ALLOWED (RCP-A6 A, not Pydantic enum).

No HTTP imports (Request/Response) — this layer is testable without ASGI (RCP-A1).
No direct DB access — storage goes through EnvironmentRepository.

Fail-closed invariant (load-bearing, RCP-A3):
  status=ready is set in EXACTLY ONE place — immediately after EnforcementActive is received.
  Search "FAIL-CLOSED GATE" to find it.
"""

from __future__ import annotations

import asyncio
import logging
from typing import NamedTuple

from .enforcement.provider import (
    EnforcementActive,
    EnforcementFailed,
    EnforcementProvider,
    FailureKind,
    ProviderHealth,
    RepoSpec,
)
from .errors import (
    ERR_ENVIRONMENT_NOT_FOUND,
    ERR_PROVISION_FAILED,
    ERR_REPO_MISMATCH,
    ERR_RUNTIME_UNAVAILABLE,
    ERR_TOOL_NOT_ALLOWED,
    RuntimeApiError,
)
from .models import CONTRACT_VERSION, Connection, Environment, RepoState
from .repository import EnvironmentRecord, EnvironmentRepository

logger = logging.getLogger(__name__)

# Tool allowlist (RCP-A6 A). Service-layer validation → 400. NOT Pydantic Enum (would give 422).
# WHY here: business rule, not schema rule. Allowlist kept near the service that enforces it.
ALLOWED_TOOLS = frozenset({"claude", "cursor", "copilot", "continue", "aider", "cody"})


def _record_to_response(record: EnvironmentRecord) -> Environment:
    """Map an EnvironmentRecord to the Environment response model."""
    connection: Connection | None = None
    if record.connection_control_url and record.connection_terminal_url:
        connection = Connection(
            control_url=record.connection_control_url,
            terminal_url=record.connection_terminal_url,
        )
    return Environment(
        project_id=record.project_id,
        status=record.status,
        phase=record.phase,
        repo=RepoState(
            url=record.repo_url,
            ref=record.repo_ref,
            cloned=(record.status not in ("provisioning", "none")),
        ),
        tool=record.tool,
        connection=connection,
        contract_version=CONTRACT_VERSION,
    )


class HealthResult(NamedTuple):
    """Healthz result returned by the service to the router."""

    status: str  # ok | degraded
    contract_version: str
    http_status: int  # 200 or 503


class LifecycleService:
    """Lifecycle state machine — stateless across calls except via repository + locks."""

    def __init__(
        self,
        repository: EnvironmentRepository,
        provider: EnforcementProvider,
    ) -> None:
        self._repo = repository
        self._provider = provider
        # Per-project-id locks. Protects read-modify-write within a single project_id.
        # Different project_ids run concurrently (lock per id, not global).
        self._locks: dict[str, asyncio.Lock] = {}
        self._locks_meta: asyncio.Lock = asyncio.Lock()

    async def _get_lock(self, project_id: str) -> asyncio.Lock:
        """Return (creating if needed) the asyncio.Lock for project_id.

        WHY separate meta-lock for lock creation: avoids TOCTOU on the _locks dict
        when two coroutines race to create a lock for the same new project_id.
        """
        async with self._locks_meta:
            if project_id not in self._locks:
                self._locks[project_id] = asyncio.Lock()
            return self._locks[project_id]

    # --- ensure ---

    async def ensure(
        self, project_id: str, repo_url: str, repo_ref: str | None, tool: str
    ) -> tuple[Environment, int]:
        """Idempotently ensure an environment exists and is ready.

        Returns (Environment, http_status) where http_status is 200 or 202.

        State machine:
          none / destroyed  → create fresh record in provisioning → call provider → gate → ready/error
          provisioning      → call provider → gate → ready/error (resume)
          asleep            → reset to provisioning → call provider → gate → ready/error (wake)
          ready (same url)  → no-op, return current (idempotent)
          ready/provisioning/asleep (diff url) → 409 ERR_REPO_MISMATCH
        """
        # Tool allowlist check — service-layer business validation → 400 (RCP-A6 A).
        if tool not in ALLOWED_TOOLS:
            raise RuntimeApiError(
                code=ERR_TOOL_NOT_ALLOWED,
                message=f"Tool {tool!r} is not allowed. Supported tools: {sorted(ALLOWED_TOOLS)}",
                http_status=400,
            )

        lock = await self._get_lock(project_id)
        async with lock:
            record = self._repo.get(project_id)

            if record is not None and record.status not in ("destroyed",):
                # Check for repo URL mismatch on a live environment (RCP-A4).
                # Compare normalized URLs (str comparison after stripping trailing slash).
                if _normalize_url(record.repo_url) != _normalize_url(repo_url):
                    raise RuntimeApiError(
                        code=ERR_REPO_MISMATCH,
                        message="Environment is bound to a different repository",
                        http_status=409,
                    )

                if record.status == "ready":
                    # Idempotent no-op for ready + same url (RCP-1c).
                    logger.info(
                        "ensure: project_id=%s already ready (idempotent)", project_id
                    )
                    return _record_to_response(record), 200

                if record.status == "asleep":
                    # Wake: reset to provisioning, then go through enforcement.
                    record.status = "provisioning"
                    record.phase = "enforcing"
                    record.connection_control_url = None
                    record.connection_terminal_url = None
                    self._repo.save(record)

                # provisioning (or just-woken): fall through to enforcement call.
            else:
                # none (record is None) or destroyed → fresh provisioning cycle (RCP-A4 / RCP-5d).
                record = EnvironmentRecord(
                    project_id=project_id,
                    status="provisioning",
                    repo_url=repo_url,
                    repo_ref=repo_ref,
                    tool=tool,
                    phase="enforcing",
                )
                self._repo.save(record)

            # --- Call enforcement provider (inside lock, under provisioning state) ---
            repo_spec = RepoSpec(url=repo_url, ref=repo_ref)
            try:
                outcome = await self._provider.ensure_active(
                    project_id, repo_spec, tool
                )
            except Exception as exc:
                # Unexpected provider exception (infra failure). Log internal detail,
                # never forward to client (RCP-A5).
                logger.exception(
                    "ensure: unexpected provider exception project_id=%s: %s",
                    project_id,
                    exc,
                )
                raise RuntimeApiError(
                    code=ERR_RUNTIME_UNAVAILABLE,
                    message="Runtime unavailable",
                    http_status=503,
                ) from None

            if isinstance(outcome, EnforcementActive):
                # ===== FAIL-CLOSED GATE (RCP-A3) — SOLE PATH TO status=ready =====
                # This is the ONLY place where status is set to "ready".
                # Removing or bypassing this block breaks the fail-closed invariant.
                record.status = "ready"
                record.phase = None
                record.connection_control_url = outcome.handle.control_url
                record.connection_terminal_url = outcome.handle.terminal_url
                self._repo.save(record)
                logger.info("ensure: project_id=%s → ready", project_id)
                return _record_to_response(record), 200
                # ===== END FAIL-CLOSED GATE =====

            # outcome is EnforcementFailed — translate kind → app-facing, NEVER by internal_code.
            assert isinstance(outcome, EnforcementFailed)
            _log_enforcement_failure(project_id, outcome)

            if outcome.kind == FailureKind.provider_unreachable:
                raise RuntimeApiError(
                    code=ERR_RUNTIME_UNAVAILABLE,
                    message="Runtime unavailable",
                    http_status=503,
                )
            # provider_error → 502 ERR_PROVISION_FAILED (RCP-A3).
            raise RuntimeApiError(
                code=ERR_PROVISION_FAILED,
                message="Provisioning failed",
                http_status=502,
            )

    # --- get ---

    async def get(self, project_id: str) -> Environment:
        """Return current state of environment. Raises 404 if never created."""
        record = self._repo.get(project_id)
        if record is None:
            raise RuntimeApiError(
                code=ERR_ENVIRONMENT_NOT_FOUND,
                message="Environment not found",
                http_status=404,
            )
        return _record_to_response(record)

    # --- sleep ---

    async def sleep(self, project_id: str) -> Environment:
        """Advisory sleep. Idempotent. Never 5xx (RCP-A4 / RCP-4c/4d).

        - none (record is None) → return synthetic 'not found' — but contract says 200 or 404 OK.
          We return 404 via RuntimeApiError which router catches and converts to 404.
          Actually spec says "200 or 404 NEVER 5xx" — router returns 404 for not-found.
        - destroyed → same 404 treatment.
        - provisioning → return current state, do NOT interrupt (spec edge case).
        - ready → transition to asleep (advisory).
        - asleep → idempotent, return current.
        """
        lock = await self._get_lock(project_id)
        async with lock:
            record = self._repo.get(project_id)
            if record is None:
                # Contract: 200 or 404 on nonexistent — raise 404 (router handles gracefully).
                raise RuntimeApiError(
                    code=ERR_ENVIRONMENT_NOT_FOUND,
                    message="Environment not found",
                    http_status=404,
                )
            if record.status == "destroyed":
                # Contract: 200 or 404 on destroyed — return current state as 200.
                return _record_to_response(record)
            if record.status == "provisioning":
                # Edge case: sleep during provisioning → return current, do NOT interrupt.
                return _record_to_response(record)
            if record.status == "ready":
                record.status = "asleep"
                record.connection_control_url = None
                record.connection_terminal_url = None
                self._repo.save(record)
            # asleep: idempotent, fall through and return.
            return _record_to_response(record)

    # --- destroy ---

    async def destroy(self, project_id: str) -> tuple[Environment, int]:
        """Idempotently destroy environment. Returns (Environment, http_status).

        Never 5xx. Returns 200/404 for nonexistent (RCP-A4 / RCP-5b/5c).
        Destroyed record is kept in repo (GET after destroy must return destroyed, RCP-5a).
        """
        lock = await self._get_lock(project_id)
        async with lock:
            record = self._repo.get(project_id)
            if record is None:
                # Contract: 200 or 404 — raise 404.
                raise RuntimeApiError(
                    code=ERR_ENVIRONMENT_NOT_FOUND,
                    message="Environment not found",
                    http_status=404,
                )
            if record.status == "destroyed":
                # Idempotent — already destroyed, return 200 with destroyed state.
                return _record_to_response(record), 200

            record.status = "destroyed"
            record.phase = None
            record.connection_control_url = None
            record.connection_terminal_url = None
            self._repo.save(record)
            logger.info("destroy: project_id=%s → destroyed", project_id)
            return _record_to_response(record), 200

    # --- healthz ---

    async def healthz(self) -> HealthResult:
        """Check provider health and return HealthResult (RCP-A3, RCP-9).

        provider unavailable → http_status=503 (never tiché ok, RCP-9c).
        provider degraded    → http_status=200, status=degraded.
        provider ok          → http_status=200, status=ok.
        """
        try:
            ph = await self._provider.health()
        except Exception as exc:
            logger.exception("healthz: provider health() raised: %s", exc)
            ph = ProviderHealth.unavailable

        if ph == ProviderHealth.unavailable:
            return HealthResult(
                status="degraded", contract_version=CONTRACT_VERSION, http_status=503
            )
        if ph == ProviderHealth.degraded:
            return HealthResult(
                status="degraded", contract_version=CONTRACT_VERSION, http_status=200
            )
        return HealthResult(
            status="ok", contract_version=CONTRACT_VERSION, http_status=200
        )


# --- helpers ---


def _normalize_url(url: str) -> str:
    """Normalize URL for mismatch comparison (strip trailing slash)."""
    return url.rstrip("/")


def _log_enforcement_failure(project_id: str, outcome: EnforcementFailed) -> None:
    """Log enforcement failure with internal_code for server-side observability.

    internal_code MUST NOT be forwarded to the client (RCP-A5).
    It is logged here for ops/debugging.
    """
    logger.warning(
        "enforcement_failed: project_id=%s kind=%s internal_code=%s",
        project_id,
        outcome.kind,
        outcome.internal_code,  # stays server-side; never reaches app-facing response
    )
