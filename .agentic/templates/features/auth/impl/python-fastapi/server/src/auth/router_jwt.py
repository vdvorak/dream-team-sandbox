from fastapi import APIRouter, Depends
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..shared.validation import ValidationResult
from .models import LoginData, RegisterData, TokenView, UserView
from .security_jwt import get_current_user, issue_token
from .service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


# write-flow: ?validate=true → dry-run (no write); else commit (201).
@router.post("/register")
async def register(body: RegisterData, validate: bool = False, db: AsyncSession = Depends(get_db)):
    svc = AuthService(db)
    if validate:
        return ValidationResult.of(await svc.validate(body))
    user = await svc.register(body)
    return JSONResponse(status_code=201, content=jsonable_encoder(user))


@router.post("/login", response_model=TokenView)
async def login(body: LoginData, db: AsyncSession = Depends(get_db)):
    user = await AuthService(db).authenticate(body)
    return TokenView(access_token=issue_token(str(user.id), user.role))


@router.get("/me", response_model=UserView)
async def me(user: UserView = Depends(get_current_user)):
    return user
