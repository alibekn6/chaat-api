from datetime import datetime, timedelta, timezone
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from passlib.context import CryptContext
from jose import jwt, JWTError
from src.auth.schema import User, PendingUser
from src.auth.models import UserCreate, TokenData
from src.auth.config import (
    SECRET_KEY,
    ALGORITHM,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    REFRESH_SECRET_KEY,
    REFRESH_TOKEN_EXPIRE_DAYS,
    EMAIL_VERIFICATION_EXPIRE_HOURS,
)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
    result = await db.execute(select(User).where(User.email == email))
    return result.scalars().first()

async def get_pending_user_by_email(db: AsyncSession, email: str) -> Optional[PendingUser]:
    result = await db.execute(select(PendingUser).where(PendingUser.email == email))
    return result.scalars().first()

async def create_pending_user(db: AsyncSession, user_in: UserCreate) -> PendingUser:
    """Create pending user for email verification"""
    hashed_pw = get_password_hash(user_in.password)
    expires_at = datetime.now(timezone.utc) + timedelta(hours=EMAIL_VERIFICATION_EXPIRE_HOURS * 2)  # Give extra time
    
    pending_user = PendingUser(
        email=user_in.email,
        hashed_password=hashed_pw,
        full_name=user_in.full_name,
        expires_at=expires_at
    )
    db.add(pending_user)
    await db.commit()
    await db.refresh(pending_user)
    return pending_user

async def create_user(db: AsyncSession, user_in: UserCreate) -> User:
    hashed_pw = get_password_hash(user_in.password)
    user = User(email=user_in.email, hashed_password=hashed_pw, full_name=user_in.full_name)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user

async def authenticate_user(db: AsyncSession, email: str, password: str) -> Optional[User]:
    user = await get_user_by_email(db, email)
    if not user or not verify_password(password, user.hashed_password):
        return None
    return user

async def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

async def create_refresh_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, REFRESH_SECRET_KEY, algorithm=ALGORITHM)

async def cleanup_expired_pending_users(db: AsyncSession) -> int:
    """Clean up expired pending users"""
    result = await db.execute(
        select(PendingUser).where(PendingUser.expires_at < datetime.now(timezone.utc))
    )
    expired_users = result.scalars().all()
    
    count = 0
    for pending_user in expired_users:
        await db.delete(pending_user)
        count += 1
    
    if count > 0:
        await db.commit()
        print(f"Cleaned up {count} expired pending users")
    
    return count