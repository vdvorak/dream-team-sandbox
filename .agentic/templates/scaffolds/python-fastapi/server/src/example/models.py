from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

# Model roles (rules/backend.md §API model role) — followed by both backend and client:


class ExampleData(BaseModel):
    """*Data — write payload for create/update/validate (the only write model)."""

    label: str = Field(min_length=1)


class ExampleView(BaseModel):
    """*View — readonly model for reading the resource."""

    id: UUID
    label: str
    created_at: datetime


class ExampleExtData(BaseModel):
    """*ExtData — read model for the init/edit flow: editable `data` + readonly context.

    Siblings of `data` (here `created_at`) are readonly form context, NEVER part of the
    write payload. Not a second write model — the write is always `ExampleData`.
    """

    data: ExampleData
    created_at: datetime
