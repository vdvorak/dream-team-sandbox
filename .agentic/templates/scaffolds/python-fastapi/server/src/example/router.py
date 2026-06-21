from fastapi import APIRouter, Depends
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..shared.collections import ApiListOf
from ..shared.validation import ValidationResult
from .models import ExampleData, ExampleView
from .service import ExampleService

router = APIRouter(tags=["example"])


@router.get("/examples", response_model=ApiListOf[ExampleView])
async def list_examples(db: AsyncSession = Depends(get_db)):
    return await ExampleService(db).list_examples()


# Write-flow (rules/backend.md §Write-flow):
#   ?validate=true  → dry-run: validation only, no write → 200 ValidationResult
#   ?validate=false → commit: server re-validates, then writes → 201 ExampleView
#                     (validation error → ApiError {code, details.field_errors}, 422)
@router.post("/examples")
async def create_or_validate(
    body: ExampleData, validate: bool = False, db: AsyncSession = Depends(get_db)
):
    svc = ExampleService(db)
    if validate:
        return ValidationResult.of(await svc.validate(body))
    created = await svc.create(body)
    return JSONResponse(status_code=201, content=jsonable_encoder(created))
