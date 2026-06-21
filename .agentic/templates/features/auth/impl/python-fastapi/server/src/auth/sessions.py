import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

_TTL_HOURS = 24


class SessionRepository:
    """Server-side sessions (stateful strategy). Token = crypto-random (secrets), single-purpose,
    revocable by delete. One row = one active session."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, user_id: str) -> str:
        token = secrets.token_urlsafe(32)
        expires = datetime.now(timezone.utc) + timedelta(hours=_TTL_HOURS)
        await self.db.execute(
            text("INSERT INTO app_session (token, user_id, expires_at) VALUES (:t, :u, :e)"),
            {"t": token, "u": user_id, "e": expires},
        )
        await self.db.commit()
        return token

    async def find_user(self, token: str):
        r = await self.db.execute(
            text(
                "SELECT u.id, u.email, u.role FROM app_session s "
                "JOIN app_user u ON u.id = s.user_id "
                "WHERE s.token = :t AND s.expires_at > :now"
            ),
            {"t": token, "now": datetime.now(timezone.utc)},
        )
        return r.mappings().first()

    async def delete(self, token: str) -> None:
        await self.db.execute(text("DELETE FROM app_session WHERE token = :t"), {"t": token})
        await self.db.commit()
