from sqlalchemy.ext.asyncio import AsyncSession

from ..shared.collections import ApiListOf
from ..shared.errors import ApiError
from .models import ExampleData, ExampleView
from .repository import ExampleRepository


class ExampleService:
    """Business logic for example. No HTTP — testable on its own."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = ExampleRepository(db)

    async def list_examples(self) -> ApiListOf[ExampleView]:
        return ApiListOf[ExampleView](items=await self.repo.list_examples())

    async def validate(self, data: ExampleData) -> dict[str, str]:
        """Business validation WITHOUT side effects (rules §Write-flow). Returns a field_errors map.
        Pydantic handles structure (min_length); here domain rules (here: unique label)."""
        errors: dict[str, str] = {}
        if await self.repo.exists_by_label(data.label):
            errors["label"] = "duplicate"
        return errors

    async def create(self, data: ExampleData) -> ExampleView:
        # Commit ALWAYS re-validates server-side — do not trust that the client called dry-run.
        errors = await self.validate(data)
        if errors:
            raise ApiError("validation_failed", status=422, details={"field_errors": errors})
        return await self.repo.create(data.label)
