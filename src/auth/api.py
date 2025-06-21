from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from google.oauth2 import id_token
from google.auth.transport import requests
from src.auth.models import UserCreate, Token, GoogleAuth, UserRead, UserUpdate
from src.auth.services import (
    get_user_by_email, create_user, authenticate_user,
    create_access_token, get_password_hash
)
from src.database import get_async_db
from src.auth.schema import User
from src.auth.config import GOOGLE_CLIENT_ID

router = APIRouter(tags=["auth"])

# Регистрация email/password
@router.post("/register", response_model=Token)
async def register(
    user_in: UserCreate,
    db: AsyncSession = Depends(get_async_db)
):
    existing = await get_user_by_email(db, user_in.email)
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    user = await create_user(db, user_in)
    access_token = await create_access_token({"sub": user.email})
    return {"access_token": access_token}

# Логин
@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_async_db)
):
    user = await authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = await create_access_token({"sub": user.email})
    return {"access_token": access_token}

# Google OAuth регистрация/логин
@router.post("/google", response_model=Token)
async def google_auth(
    payload: GoogleAuth,
    db: AsyncSession = Depends(get_async_db)
):
    try:
        idinfo = id_token.verify_oauth2_token(
            payload.id_token,
            requests.Request(),
            GOOGLE_CLIENT_ID
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid Google token")
    email = idinfo.get("email")
    google_id = idinfo.get("sub")
    user = await get_user_by_email(db, email)
    if not user:
        # создаём нового
        user = User(
            email=email,
            hashed_password=get_password_hash(google_id),  # временный
            full_name=idinfo.get("name"),
            is_verified=True,
            google_id=google_id
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
    access_token = await create_access_token({"sub": user.email})
    return {"access_token": access_token}

# CRUD для пользователей
@router.get("/users/{user_id}", response_model=UserRead)
async def read_user(
    user_id: int,
    db: AsyncSession = Depends(get_async_db)
):
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@router.put("/users/{user_id}", response_model=UserRead)
async def update_user(
    user_id: int,
    user_up: UserUpdate,
    db: AsyncSession = Depends(get_async_db)
):
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    for var, value in user_up.dict(exclude_unset=True).items():
        setattr(user, var, value)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user

@router.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    db: AsyncSession = Depends(get_async_db)
):
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    await db.delete(user)
    await db.commit()
    return {"detail": "User deleted"}
