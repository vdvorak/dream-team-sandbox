"""Runtime control-plane router — HTTP layer only (RCP-A1).

Responsibilities:
  - Route definitions (path/method → handler).
  - Extract path params, decode request body, inject service via Depends.
  - Validate Bearer token (auth dependency) → 401 ERR_UNAUTHORIZED (RCP-A7).
  - Serialize service result to JSONResponse with correct status code.
  - Map RuntimeApiError → JSON error envelope (via registered exception handler).

MUST NOT:
  - Contain lifecycle logic or state-machine decisions.
  - Call enforcement provider directly.
  - Import asyncio / threading primitives (concurrency lives in service).

DI pattern:
  Handlers use Depends(get_lifecycle_service) and Depends(get_service_token).
  Both are module-level dependency callables so FastAPI can override them via
  app.dependency_overrides in the app factory (for testing and per-instance config).
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Path
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .errors import ERR_UNAUTHORIZED, RuntimeApiError
from .models import EnsureRequest, Environment
from .service import LifecycleService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1")

# HTTPBearer extracts "Authorization: Bearer <token>".
# auto_error=False so we raise 401 (not 403) ourselves (RCP-14a).
_bearer_scheme = HTTPBearer(auto_error=False)


# --- Dependency stubs (overridden per-app by create_runtime_app) ---


def get_lifecycle_service() -> LifecycleService:
    """Dependency stub — overridden by create_runtime_app via dependency_overrides."""
    raise RuntimeError(
        "LifecycleService not initialized. Use create_runtime_app() to build a configured app."
    )


def get_service_token() -> str:
    """Dependency stub — overridden by create_runtime_app via dependency_overrides."""
    raise RuntimeError(
        "service_token not configured. Use create_runtime_app() to build a configured app."
    )


# --- Auth dependency ---


async def verify_service_token(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    expected_token: str = Depends(get_service_token),
) -> None:
    """Guard: verify Bearer token. Raises 401 if missing or wrong (RCP-14a)."""
    if credentials is None or credentials.credentials != expected_token:
        logger.warning("auth: missing or invalid Bearer token")
        raise RuntimeApiError(
            code=ERR_UNAUTHORIZED,
            message="Missing or invalid service identity",
            http_status=401,
        )


# --- healthz (public, no auth per RCP-A7 / RCP-14c) ---


@router.get("/healthz", tags=["meta"])
async def healthz(
    service: LifecycleService = Depends(get_lifecycle_service),
) -> JSONResponse:
    """Public health endpoint. No auth required (security: [] in OpenAPI, RCP-14c)."""
    result = await service.healthz()
    body = {"status": result.status, "contract_version": result.contract_version}
    return JSONResponse(status_code=result.http_status, content=body)


# --- lifecycle endpoints (all require auth) ---


@router.post(
    "/environments/{project_id}/ensure",
    response_model=Environment,
    tags=["lifecycle"],
)
async def ensure_environment(
    project_id: str = Path(pattern=r"^[A-Za-z0-9_-]+$", min_length=1, max_length=128),
    body: EnsureRequest = ...,
    _auth: None = Depends(verify_service_token),
    service: LifecycleService = Depends(get_lifecycle_service),
) -> JSONResponse:
    """Idempotently create/restore environment (RCP-1)."""
    env, http_status = await service.ensure(
        project_id=project_id,
        repo_url=str(body.repo.url),
        repo_ref=body.repo.ref,
        tool=body.tool,
    )
    if http_status == 202:
        return JSONResponse(
            status_code=202,
            content=env.model_dump(exclude_none=False),
            headers={"Retry-After": "2"},
        )
    return JSONResponse(status_code=200, content=env.model_dump(exclude_none=False))


@router.get(
    "/environments/{project_id}",
    response_model=Environment,
    tags=["lifecycle"],
)
async def get_environment(
    project_id: str = Path(pattern=r"^[A-Za-z0-9_-]+$", min_length=1, max_length=128),
    _auth: None = Depends(verify_service_token),
    service: LifecycleService = Depends(get_lifecycle_service),
) -> JSONResponse:
    """Return current environment state (RCP-3)."""
    env = await service.get(project_id)
    return JSONResponse(status_code=200, content=env.model_dump(exclude_none=False))


@router.post(
    "/environments/{project_id}/sleep",
    response_model=Environment,
    tags=["lifecycle"],
)
async def sleep_environment(
    project_id: str = Path(pattern=r"^[A-Za-z0-9_-]+$", min_length=1, max_length=128),
    _auth: None = Depends(verify_service_token),
    service: LifecycleService = Depends(get_lifecycle_service),
) -> JSONResponse:
    """Advisory sleep (RCP-4). Idempotent; never 5xx."""
    env = await service.sleep(project_id)
    return JSONResponse(status_code=200, content=env.model_dump(exclude_none=False))


@router.delete(
    "/environments/{project_id}",
    response_model=Environment,
    tags=["lifecycle"],
)
async def destroy_environment(
    project_id: str = Path(pattern=r"^[A-Za-z0-9_-]+$", min_length=1, max_length=128),
    _auth: None = Depends(verify_service_token),
    service: LifecycleService = Depends(get_lifecycle_service),
) -> JSONResponse:
    """Destroy environment idempotently (RCP-5). Never 5xx."""
    env, http_status = await service.destroy(project_id)
    return JSONResponse(
        status_code=http_status, content=env.model_dump(exclude_none=False)
    )
