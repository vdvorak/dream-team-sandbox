from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

_COLS = "id, email, password_hash, role"


class AuthRepository:
    """Single DB access point for users. SQLAlchemy Core text() SQL, no business logic."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def find_by_email(self, email: str):
        r = await self.db.execute(
            text(f"SELECT {_COLS} FROM app_user WHERE email = :e"), {"e": email}
        )
        return r.mappings().first()

    async def find_by_id(self, uid: str):
        r = await self.db.execute(
            text(f"SELECT {_COLS} FROM app_user WHERE id = :i"), {"i": uid}
        )
        return r.mappings().first()

    async def exists_by_email(self, email: str) -> bool:
        r = await self.db.execute(
            text("SELECT 1 FROM app_user WHERE email = :e LIMIT 1"), {"e": email}
        )
        return r.first() is not None

    async def create(self, email: str, password_hash: str) -> dict:
        row = {
            "id": str(uuid4()),
            "email": email,
            "password_hash": password_hash,
            "role": "user",
            "created_at": datetime.now(timezone.utc),
        }
        await self.db.execute(
            text(
                "INSERT INTO app_user (id, email, password_hash, role, created_at) "
                "VALUES (:id, :email, :password_hash, :role, :created_at)"
            ),
            row,
        )
        await self.db.commit()
        return row
