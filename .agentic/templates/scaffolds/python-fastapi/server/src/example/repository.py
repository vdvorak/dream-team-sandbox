from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from .models import ExampleView


def _row_to_view(m) -> ExampleView:
    return ExampleView(id=m["id"], label=m["label"], created_at=m["created_at"])


class ExampleRepository:
    """Single DB access point for example (one table = one repository).
    SQLAlchemy Core text() SQL, no business logic."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_examples(self) -> list[ExampleView]:
        result = await self.db.execute(
            text("SELECT id, label, created_at FROM example ORDER BY created_at DESC")
        )
        return [_row_to_view(m) for m in result.mappings().all()]

    async def exists_by_label(self, label: str) -> bool:
        result = await self.db.execute(
            text("SELECT 1 FROM example WHERE label = :label LIMIT 1"), {"label": label}
        )
        return result.first() is not None

    async def create(self, label: str) -> ExampleView:
        row = {"id": str(uuid4()), "label": label, "created_at": datetime.now(timezone.utc)}
        await self.db.execute(
            text("INSERT INTO example (id, label, created_at) VALUES (:id, :label, :created_at)"),
            row,
        )
        await self.db.commit()
        return ExampleView(id=UUID(row["id"]), label=label, created_at=row["created_at"])
