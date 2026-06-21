"""RuntimeApiError — net-new error type for runtime control-plane (RCP-A6 B).

WHY net-new and not scaffold shared/errors.py:
  Scaffold shape is {code, details} (missing message, wrong key).
  Contract §8 requires {code, message, detail?} — different shape.
  These MUST NOT be mixed; this module is runtime-local (reuse decision: feature-local).

App-facing error codes per contract §8 only.
Internal cage codes (contracts/error-codes.md) MUST NEVER appear here (RCP-A5).
"""

from __future__ import annotations

import logging

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

# App-facing error code constants (contract §8 — closed set).
ERR_ENVIRONMENT_NOT_FOUND = "ERR_ENVIRONMENT_NOT_FOUND"
ERR_ENVIRONMENT_NOT_READY = "ERR_ENVIRONMENT_NOT_READY"
ERR_ENVIRONMENT_DESTROYING = "ERR_ENVIRONMENT_DESTROYING"
ERR_REPO_MISMATCH = "ERR_REPO_MISMATCH"
ERR_CLONE_FAILED = "ERR_CLONE_FAILED"
ERR_PROVISION_FAILED = "ERR_PROVISION_FAILED"
ERR_PATH_ESCAPE = "ERR_PATH_ESCAPE"
ERR_TOOL_NOT_ALLOWED = "ERR_TOOL_NOT_ALLOWED"
ERR_UNAUTHORIZED = "ERR_UNAUTHORIZED"
ERR_RUNTIME_UNAVAILABLE = "ERR_RUNTIME_UNAVAILABLE"
# Added in contract v1.1.0 (RCP-A6, §8): covers all schema-level 400s (extra fields,
# missing required, wrong type, invalid repo.url). Replaces the previous ERR_CLONE_FAILED
# misuse for structural validation errors — ERR_CLONE_FAILED is reserved for clone execution
# failures, not for request-shape violations.
ERR_INVALID_REQUEST = "ERR_INVALID_REQUEST"

# Closed set for quick membership checks (guards against accidental cage code leak).
APP_FACING_CODES = frozenset({
    ERR_ENVIRONMENT_NOT_FOUND,
    ERR_ENVIRONMENT_NOT_READY,
    ERR_ENVIRONMENT_DESTROYING,
    ERR_REPO_MISMATCH,
    ERR_CLONE_FAILED,
    ERR_PROVISION_FAILED,
    ERR_PATH_ESCAPE,
    ERR_TOOL_NOT_ALLOWED,
    ERR_UNAUTHORIZED,
    ERR_RUNTIME_UNAVAILABLE,
    ERR_INVALID_REQUEST,
})


class RuntimeApiError(Exception):
    """Domain error carrying an app-facing code, HTTP status, human message, and optional detail.

    detail is a plain dict (never contains cage internals, stack traces, or BYOK tokens).
    """

    def __init__(
        self,
        code: str,
        message: str,
        http_status: int,
        detail: dict | None = None,
    ) -> None:
        if code not in APP_FACING_CODES:
            # Guard: if a cage code ever leaks here, fail loudly server-side (log)
            # but return a generic error to the client (nepropustnost RCP-A5).
            logger.error(
                "runtime_api_error: non-app-facing code %r attempted — replaced with ERR_RUNTIME_UNAVAILABLE",
                code,
            )
            code = ERR_RUNTIME_UNAVAILABLE
            message = "Runtime unavailable"
        self.code = code
        self.message = message
        self.http_status = http_status
        self.detail = detail
        super().__init__(message)


async def runtime_api_error_handler(request: Request, exc: RuntimeApiError) -> JSONResponse:
    """Serialize RuntimeApiError to contract §8 envelope {code, message, detail?}."""
    body: dict = {"code": exc.code, "message": exc.message}
    if exc.detail is not None:
        body["detail"] = exc.detail
    return JSONResponse(status_code=exc.http_status, content=body)


async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Map ALL Pydantic/schema RequestValidationError → 400 ERR_INVALID_REQUEST.

    WHY override default 422:
    - extra_forbidden on EnsureRequest/RepoInput = enforcement-bypass attempt → 400 (RCP-1h, AC-12c).
    - Missing required field, wrong type, invalid repo.url → also 400 for consistency.

    WHY ERR_INVALID_REQUEST (not ERR_CLONE_FAILED):
    - Contract v1.1.0 added ERR_INVALID_REQUEST for exactly this purpose (RCP-A6 §8).
    - ERR_CLONE_FAILED is reserved for clone execution failures (the git clone step).
      Using it for structural validation was semantically wrong; fixed in this bump.

    Envelope: {code, message} — detail omitted (schema validation details must never
    carry internal paths or cage names that could aid bypass enumeration, RCP-A5).
    """
    errors = exc.errors()
    logger.debug("validation_error: %s", errors)

    # Extra fields on top-level body or nested repo object = bypass attempt (RCP-12b, AC-12c).
    if any(e.get("type") == "extra_forbidden" for e in errors):
        return JSONResponse(
            status_code=400,
            content={
                "code": ERR_INVALID_REQUEST,
                "message": "Extra fields are not allowed in request body",
            },
        )

    # All other schema errors: missing required, wrong type, invalid repo.url.
    return JSONResponse(
        status_code=400,
        content={
            "code": ERR_INVALID_REQUEST,
            "message": "Request validation failed",
        },
    )
