from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from backend.src.database import get_db
from backend.src.auth import create_access_token, get_current_user
from backend.src.services.auth_service import authenticate_user
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str
    user: dict


async def _do_login(username: str, password: str, db: AsyncSession):
    user = await authenticate_user(db, username, password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password"
        )
    access_token = create_access_token(data={"sub": user.username})
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "role": user.role
        }
    }


@router.post("/login", response_model=Token)
async def login(request: Request, db: AsyncSession = Depends(get_db)):
    """Login via JSON body or form data."""
    content_type = request.headers.get("content-type", "")
    
    if "application/json" in content_type:
        # JSON login (from our dashboard frontend)
        body = await request.json()
        username = body.get("username", "")
        password = body.get("password", "")
    else:
        # Form data login (for OAuth2 / Swagger UI)
        form = await request.form()
        username = form.get("username", "")
        password = form.get("password", "")
    
    return await _do_login(username, password, db)


@router.get("/me")
async def get_me(current_user=Depends(get_current_user)):
    return {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "role": current_user.role,
        "is_active": current_user.is_active
    }


@router.post("/logout")
async def logout():
    return {"message": "Successfully logged out"}
