import os
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..shared.errors import ApiError
from .models import UserView
from .repository import AuthRepository

# Stateless JWT strategy. No server-side store; revoke = short TTL. Secret from APP_SECRET_KEY.
_ALG = "HS256"
_TTL_MIN = 30


def _secret() -> str:
    # Dev fallback is ≥ 32 bytes (HS256 minimum); production MUST set APP_SECRET_KEY.
    return os.environ.get("APP_SECRET_KEY", "dev-insecure-change-me-not-for-production")


def issue_token(user_id: str, role: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {"sub": user_id, "role": role, "exp": now + timedelta(minutes=_TTL_MIN)}
    return jwt.encode(payload, _secret(), algorithm=_ALG)


async def get_current_user(
    authorization: str = Header(default=""), db: AsyncSession = Depends(get_db)
) -> UserView:
    if not authorization.startswith("Bearer "):
        raise ApiError("unauthorized", status=401)
    try:
        payload = jwt.decode(authorization[7:], _secret(), algorithms=[_ALG])
    except jwt.PyJWTError:
        raise ApiError("unauthorized", status=401)
    user = await AuthRepository(db).find_by_id(payload.get("sub"))
    if user is None:
        raise ApiError("unauthorized", status=401)
    return UserView(id=user["id"], email=user["email"], role=user["role"])
