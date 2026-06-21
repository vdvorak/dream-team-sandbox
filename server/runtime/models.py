"""Pydantic v2 models for runtime control-plane — exact shape per runtime.openapi.yaml.

Key decisions:
- extra="forbid" on EnsureRequest AND its nested RepoInput model (RCP-A6 D, AC-12c).
  This ensures extra fields like firewall/egress/policy → 422 at Pydantic level,
  converted to 400 by the router exception handler (overrides FastAPI's default 422 for
  additionalProperties violations, which map to RequestValidationError).
- tool is str (not Enum) — tool allowlist validation is service-level → 400 (RCP-A6 A).
- connection is Connection | None (not oneOf — FastAPI generates anyOf which is semantically
  equivalent per RCP-A6 C tolerance note).
- contract_version is a constant "1.1.0" injected by service into every Environment response.
"""

from __future__ import annotations

from pydantic import AnyUrl, ConfigDict, model_validator
from pydantic import BaseModel


CONTRACT_VERSION = "1.1.0"


class RepoInput(BaseModel):
    """Nested repo object inside EnsureRequest. extra=forbid blocks bypass fields (RCP-A6 D)."""

    model_config = ConfigDict(extra="forbid")

    url: AnyUrl
    ref: str | None = None


class EnsureRequest(BaseModel):
    """Request body for POST /environments/{project_id}/ensure.

    extra=forbid rejects unknown fields (firewall, egress, policy, BYOK token …) → 400 (RCP-A6 D).
    tool is str (not Enum) — service validates against allowlist → 400 (RCP-A6 A).
    """

    model_config = ConfigDict(extra="forbid")

    repo: RepoInput
    tool: str

    @model_validator(mode="after")
    def _tool_not_empty(self) -> "EnsureRequest":
        # Structural non-emptiness only — business allowlist lives in service.
        if not self.tool.strip():
            raise ValueError("tool must not be empty")
        return self


class Connection(BaseModel):
    """Opaque connection handle (RCP-A2). No substrate identifiers (RCP-A6 E)."""

    control_url: str
    terminal_url: str


class RepoState(BaseModel):
    """Repo state included in every Environment response."""

    url: str
    ref: str | None = None
    cloned: bool


class Environment(BaseModel):
    """Canonical Environment response shape per OpenAPI schema."""

    project_id: str
    status: str  # provisioning | ready | asleep | destroyed
    phase: str | None = None
    repo: RepoState
    tool: str
    connection: Connection | None = None
    contract_version: str = CONTRACT_VERSION


class Health(BaseModel):
    """Healthz response (RCP-9)."""

    status: str  # ok | degraded
    contract_version: str = CONTRACT_VERSION


class ErrorResponse(BaseModel):
    """App-facing error envelope per contract §8 (code + message + optional detail object).

    WHY not scaffold shared/errors.py: scaffold uses {code, details} (wrong shape).
    Contract requires {code, message, detail} (RCP-A6 B).
    """

    code: str
    message: str
    detail: dict | None = None
