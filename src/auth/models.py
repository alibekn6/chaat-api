from pydantic import BaseModel, EmailStr, field_validator, model_validator
from typing import Optional, Any, Dict
from datetime import datetime
import re


class UserCreate(BaseModel):
    email: str  # Changed from EmailStr to str for custom validation
    password: str
    full_name: str  # Made required, removed Optional

    @model_validator(mode='before')
    @classmethod
    def clean_data(cls, data: Any) -> Any:
        """Clean and normalize data before field validation"""
        if isinstance(data, dict):
            # Clean email - lowercase and strip
            if 'email' in data and data['email']:
                data['email'] = str(data['email']).lower().strip()
            
            # Clean full_name - strip spaces
            if 'full_name' in data and data['full_name']:
                data['full_name'] = str(data['full_name']).strip()
        
        return data

    @field_validator('email')
    @classmethod
    def validate_email(cls, v):
        if not v or not v.strip():
            raise ValueError('Email is required')
        
        # Email format validation
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, v):
            raise ValueError('Please enter a valid email address')
        return v
    
    @field_validator('password')
    @classmethod
    def validate_password(cls, v):
        if not v:
            raise ValueError('Password is required')
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        return v
    
    @field_validator('full_name')
    @classmethod
    def validate_full_name(cls, v):
        if not v or not v.strip():
            raise ValueError('Full name is required')
        if len(v) < 2:
            raise ValueError('Full name must be at least 2 characters long')
        return v


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
    refresh_token: str
    token_type: str = "bearer"


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class TokenData(BaseModel):
    email: Optional[str] = None


class GoogleCodeAuth(BaseModel):
    code: str


class LoginRequest(BaseModel):
    email: str  # Changed from EmailStr to str for custom validation
    password: str

    @model_validator(mode='before')
    @classmethod
    def clean_data(cls, data: Any) -> Any:
        """Clean and normalize data before field validation"""
        if isinstance(data, dict):
            # Clean email - lowercase and strip
            if 'email' in data and data['email']:
                data['email'] = str(data['email']).lower().strip()
        
        return data

    @field_validator('email')
    @classmethod
    def validate_email(cls, v):
        if not v or not v.strip():
            raise ValueError('Email is required')
        
        # Email format validation
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, v):
            raise ValueError('Please enter a valid email address')
        return v
    
    @field_validator('password')
    @classmethod
    def validate_password(cls, v):
        if not v:
            raise ValueError('Password is required')
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        return v


# Registration Response (before email verification)
class RegistrationResponse(BaseModel):
    message: str
    email: str
    verification_sent: bool


# Pending User Models
class PendingUserRead(BaseModel):
    id: int
    email: EmailStr
    full_name: Optional[str]
    created_at: datetime
    expires_at: datetime

    class Config:
        from_attributes = True


# Email Verification Models
class EmailVerificationRequest(BaseModel):
    email: EmailStr


class EmailVerificationResponse(BaseModel):
    message: str
    email: str


class VerifyEmailRequest(BaseModel):
    token: str


class VerifyEmailResponse(BaseModel):
    message: str
    is_verified: bool
    tokens: Optional[Token] = None  # Return tokens after successful verification


class EmailVerificationRead(BaseModel):
    id: int
    user_id: Optional[int] = None
    pending_user_id: Optional[int] = None
    verification_token: str
    created_at: datetime
    expires_at: datetime
    is_used: bool

    class Config:
        from_attributes = True


# Rate Limiting Models
class RateLimitRead(BaseModel):
    id: int
    ip_address: str
    endpoint: str
    request_count: int
    window_start: datetime
    last_request: datetime

    class Config:
        from_attributes = True


class UserCreateGoogle(BaseModel):
    email: str
    full_name: str

    @model_validator(mode='before')
    @classmethod
    def clean_data(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if 'email' in data and data['email']:
                data['email'] = str(data['email']).lower().strip()
            if 'full_name' in data and data['full_name']:
                data['full_name'] = str(data['full_name']).strip()
        return data

    @field_validator('email')
    @classmethod
    def validate_email(cls, v):
        if not v or not v.strip():
            raise ValueError('Email is required')
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, v):
            raise ValueError('Please enter a valid email address')
        return v

    @field_validator('full_name')
    @classmethod
    def validate_full_name(cls, v):
        if not v or not v.strip():
            raise ValueError('Full name is required')
        if len(v) < 2:
            raise ValueError('Full name must be at least 2 characters long')
        return v