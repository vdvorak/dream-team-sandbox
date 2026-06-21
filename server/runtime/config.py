"""Runtime control-plane configuration via pydantic-settings (RCP-A2).

WHY pydantic-settings and not plain os.environ:
  - Type-validated, with defaults.
  - Consistent with scaffold pattern (stack §pydantic-settings config).
  - enforcement_provider: dev | cage governs which EnforcementProvider implementation is used.
  - service_token: used in dev mode for App→Runtime auth (RCP-A7).

Default enforcement_provider = "dev" (safe; never "cage" without explicit config).
"""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings


class RuntimeSettings(BaseSettings):
    """Configuration for the runtime control-plane server."""

    # Which enforcement provider to instantiate: "dev" or "cage".
    # Default "dev" — never accidentally start with cage (which is a stub in slice 1).
    enforcement_provider: str = "dev"

    # Dev provider test mode: "active" | "fail" | "down" (only used when enforcement_provider=dev).
    dev_provider_mode: str = "active"

    # Service token for App→Runtime auth (slice 1 dev-mode Bearer token, RCP-A7).
    # In production this is a secret; in tests it is overridden directly.
    service_token: str = "dev-token-change-me-in-production"

    # Fly.io provider config (only used when enforcement_provider=cage).
    fly_api_token: str = ""
    fly_app_name: str = ""

    # Workspace root path — injectable for tests (default matches production cage layout).
    workspace_root: str = "/workspace"

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


@lru_cache
def get_runtime_settings() -> RuntimeSettings:
    return RuntimeSettings()
