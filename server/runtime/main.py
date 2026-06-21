"""Runtime control-plane FastAPI application factory.

Usage (local):
    cd <repo-root>
    uvicorn server.runtime.main:app --reload --port 8080

Or:
    python -m uvicorn server.runtime.main:app --port 8080

Auth in dev mode:
    Authorization: Bearer dev-token-change-me-in-production
    (configurable via SERVICE_TOKEN env var / .env)

Note: state persists in-memory for the duration of the process. Restart = empty state (slice 1).
"""

from __future__ import annotations

import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError

from .config import get_runtime_settings
from .enforcement.dev import DevEnforcementProvider
from .errors import RuntimeApiError, runtime_api_error_handler, validation_error_handler
from .repository import EnvironmentRepository
from .router import get_lifecycle_service, get_service_token, router
from .service import LifecycleService
from .workspace import WorkspaceAccessor

logger = logging.getLogger(__name__)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)


def create_runtime_app(
    service_token: str | None = None,
    enforcement_provider_override=None,
    workspace_accessor_override=None,
) -> FastAPI:
    """Create and configure the runtime control-plane FastAPI application.

    Args:
        service_token: Override the service token (for testing). If None, uses settings.
        enforcement_provider_override: Inject a specific provider instance (for testing).
            If None, uses the configured enforcement_provider setting.
        workspace_accessor_override: Inject a WorkspaceAccessor instance (for testing).
            If None, creates one from settings.workspace_root.
    """
    settings = get_runtime_settings()
    effective_token = (
        service_token if service_token is not None else settings.service_token
    )

    if enforcement_provider_override is not None:
        provider = enforcement_provider_override
    else:
        provider = _build_provider(settings)

    if workspace_accessor_override is not None:
        workspace_accessor = workspace_accessor_override
    else:
        workspace_root = Path(settings.workspace_root)
        workspace_accessor = WorkspaceAccessor(workspace_root=workspace_root)

    repository = EnvironmentRepository()
    service = LifecycleService(
        repository=repository,
        provider=provider,
        workspace_accessor=workspace_accessor,
    )

    app = FastAPI(
        title="Runtime Control Plane",
        version="1.1.0",
        description="Substrátem-agnostický lifecycle control-plane (contract v1.1.0).",
    )

    # Register exception handlers.
    app.add_exception_handler(RuntimeApiError, runtime_api_error_handler)
    # Override FastAPI's default 422 for validation errors → 400 per contract (RCP-1h, AC-12c).
    app.add_exception_handler(RequestValidationError, validation_error_handler)

    # Override the dependency stubs defined in router.py.
    # WHY: each app instance (including test instances) gets its own service and token.
    # FastAPI resolves dependencies by callable identity, so we override the exact stubs.
    def _service_provider() -> LifecycleService:
        return service

    def _token_provider() -> str:
        return effective_token

    app.dependency_overrides[get_lifecycle_service] = _service_provider
    app.dependency_overrides[get_service_token] = _token_provider

    app.include_router(router)

    logger.info(
        "runtime_app_created provider=%s",
        type(provider).__name__,
    )
    return app


def _build_provider(settings):
    """Instantiate the enforcement provider based on config (RCP-A2)."""
    ptype = settings.enforcement_provider.lower()
    if ptype == "dev":
        return DevEnforcementProvider(mode=settings.dev_provider_mode)
    if ptype == "cage":
        from .enforcement.cage import CageEnforcementProvider
        from server.cage.providers.fly_provider import FlyProvider

        cage_runtime = FlyProvider(
            api_token=settings.fly_api_token,
            app_name=settings.fly_app_name,
        )
        return CageEnforcementProvider(cage_runtime=cage_runtime)
    # Unknown provider → fail at startup rather than silently operating insecure.
    raise ValueError(
        f"Unknown enforcement_provider {ptype!r}. Must be 'dev' or 'cage'."
    )


# Module-level app instance for uvicorn.
app = create_runtime_app()
