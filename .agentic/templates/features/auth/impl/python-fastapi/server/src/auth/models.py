from uuid import UUID

from pydantic import BaseModel, Field

# Model roles (rules/backend.md §API model role).


class RegisterData(BaseModel):
    """*Data — registration payload."""

    email: str = Field(min_length=3)
    password: str = Field(min_length=8)


class LoginData(BaseModel):
    """*Data — login payload."""

    email: str
    password: str


class UserView(BaseModel):
    """*View — readonly user model (never exposes password_hash)."""

    id: UUID
    email: str
    role: str


class TokenView(BaseModel):
    access_token: str
    token_type: str = "bearer"
