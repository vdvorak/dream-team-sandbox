from fastapi import Cookie, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..shared.errors import ApiError
from .models import UserView
from .sessions import SessionRepository

# Stateful server-side session strategy. The session token travels in an httpOnly cookie;
# revoke = delete the row (logout). Trades scalability for easy revocation.
COOKIE = "session"


async def get_current_user(
    session: str = Cookie(default=""), db: AsyncSession = Depends(get_db)
) -> UserView:
    if not session:
        raise ApiError("unauthorized", status=401)
    user = await SessionRepository(db).find_user(session)
    if user is None:
        raise ApiError("unauthorized", status=401)
    return UserView(id=user["id"], email=user["email"], role=user["role"])
