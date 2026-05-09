from datetime import datetime, timedelta, timezone

import jwt
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.config import settings
from app.middleware.auth import CurrentAdmin
from app.models.admin import Admin
from app.security.password import verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    token: str
    username: str


@router.post("/login", response_model=LoginResponse)
async def login(body: LoginRequest):
    admin = await Admin.find_one(Admin.username == body.username.lower().strip())
    if not admin or not verify_password(body.password, admin.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sai tên đăng nhập hoặc mật khẩu")

    expire = datetime.now(timezone.utc) + timedelta(days=settings.jwt_expires_days)
    token = jwt.encode(
        {"sub": str(admin.id), "username": admin.username, "exp": expire},
        settings.jwt_secret,
        algorithm="HS256",
    )
    return LoginResponse(token=token, username=admin.username)


@router.get("/me")
async def me(admin: CurrentAdmin):
    return {"id": str(admin.id), "username": admin.username, "created_at": admin.created_at}
