from pydantic import BaseModel, EmailStr
from typing import Optional

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = None

class UserRead(BaseModel):
    id: int
    email: EmailStr
    full_name: Optional[str]
    is_active: bool
    is_verified: bool
    is_superuser: bool

    class Config:
        from_attributes = True

class UserUpdate(BaseModel):
    full_name: Optional[str]
    is_active: Optional[bool]

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class TokenData(BaseModel):
    email: Optional[str] = None

class GoogleAuth(BaseModel):
    id_token: str