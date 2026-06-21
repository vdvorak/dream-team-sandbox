from fastapi import APIRouter, Cookie, Depends, Response
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..shared.validation import ValidationResult
from .models import LoginData, RegisterData, UserView
from .security_session import COOKIE, get_current_user
from .service import AuthService
from .sessions import SessionRepository

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register")
async def register(body: RegisterData, validate: bool = False, db: AsyncSession = Depends(get_db)):
    svc = AuthService(db)
    if validate:
        return ValidationResult.of(await svc.validate(body))
    user = await svc.register(body)
    return JSONResponse(status_code=201, content=jsonable_encoder(user))


@router.post("/login")
async def login(body: LoginData, response: Response, db: AsyncSession = Depends(get_db)):
    user = await AuthService(db).authenticate(body)
    token = await SessionRepository(db).create(str(user.id))
    response.set_cookie(COOKIE, token, httponly=True, samesite="lax", max_age=86400)
    return {"ok": True}


@router.post("/logout")
async def logout(
    response: Response, session: str = Cookie(default=""), db: AsyncSession = Depends(get_db)
):
    if session:
        await SessionRepository(db).delete(session)
    response.delete_cookie(COOKIE)
    return {"ok": True}


@router.get("/me", response_model=UserView)
async def me(user: UserView = Depends(get_current_user)):
    return user
