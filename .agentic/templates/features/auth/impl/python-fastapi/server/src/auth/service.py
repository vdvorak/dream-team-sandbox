from sqlalchemy.ext.asyncio import AsyncSession

from ..shared.errors import ApiError
from .models import LoginData, RegisterData, UserView
from .passwords import hash_password, verify_password
from .repository import AuthRepository


class AuthService:
    """Auth business logic (strategy-agnostic). No HTTP — testable on its own."""

    def __init__(self, db: AsyncSession):
        self.repo = AuthRepository(db)

    async def validate(self, data: RegisterData) -> dict[str, str]:
        # Side-effect-free (rules §Write-flow): unique email.
        errors: dict[str, str] = {}
        if await self.repo.exists_by_email(data.email):
            errors["email"] = "duplicate"
        return errors

    async def register(self, data: RegisterData) -> UserView:
        # Commit ALWAYS re-validates server-side.
        errors = await self.validate(data)
        if errors:
            raise ApiError("validation_failed", status=422, details={"field_errors": errors})
        row = await self.repo.create(data.email, hash_password(data.password))
        return UserView(id=row["id"], email=row["email"], role=row["role"])

    async def authenticate(self, data: LoginData) -> UserView:
        # Verify credentials; SAME error for an unknown email and a wrong password (no enumeration).
        user = await self.repo.find_by_email(data.email)
        if user is None or not verify_password(data.password, user["password_hash"]):
            raise ApiError("invalid_credentials", status=401)
        return UserView(id=user["id"], email=user["email"], role=user["role"])
