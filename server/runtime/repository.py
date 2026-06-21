"""EnvironmentRepository — in-memory storage for Environment records (slice 1, RCP-A1).

Storage layer only: holds state, zero business logic, zero fail-closed decisions.
No SQLAlchemy / DB — slice 1 is in-memory (touches_db: false, RCP-A1).

WHY keep destroyed records: contract §2 + RCP-5d require that:
  - GET after destroy returns status=destroyed (not 404)
  - ensure after destroy starts a fresh cycle (the record IS there, service resets it)
Record deletion would break both invariants. Destroyed records are small (just metadata).

Thread safety: asyncio.Lock per project_id lives in the SERVICE, not here (RCP-A1).
Repository itself is called only under that lock for any given project_id.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class EnvironmentRecord:
    """Mutable in-memory record for a single environment.

    Fields map to the Environment response schema.
    connection_handle is stored as a tuple (control_url, terminal_url) or None.
    """

    project_id: str
    status: str  # provisioning | ready | asleep | destroyed
    repo_url: str
    repo_ref: str | None
    tool: str
    phase: str | None = None
    connection_control_url: str | None = None
    connection_terminal_url: str | None = None


class EnvironmentRepository:
    """In-memory dict-backed repository for EnvironmentRecord objects.

    No concurrency management here — callers (service) hold asyncio.Lock per project_id.
    """

    def __init__(self) -> None:
        self._store: dict[str, EnvironmentRecord] = {}

    def get(self, project_id: str) -> EnvironmentRecord | None:
        """Return the record for project_id, or None if never created."""
        return self._store.get(project_id)

    def save(self, record: EnvironmentRecord) -> None:
        """Insert or replace the record for record.project_id."""
        self._store[record.project_id] = record

    def all_project_ids(self) -> list[str]:
        """Return all known project IDs (for diagnostics/iteration)."""
        return list(self._store.keys())
