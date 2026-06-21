from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text

from ..database import get_session_factory

router = APIRouter(tags=["system-health"])


@router.get("/health")
async def get_health():
    return {"status": "ok"}


@router.get("/health/deep")
async def get_health_deep():
    try:
        factory = get_session_factory()
        async with factory() as session:
            await session.execute(text("SELECT 1"))
        return {"status": "ok"}
    except Exception:
        return JSONResponse(
            status_code=503, content={"status": "unavailable", "details": {"dep": "db"}}
        )
