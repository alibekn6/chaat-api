from fastapi import APIRouter, Depends, HTTPException, status, Request, Body
from jose import JWTError
import jwt
from sqlalchemy.ext.asyncio import AsyncSession
from google.oauth2 import id_token
from google.auth.transport import requests
import httpx
from urllib.parse import urlencode
from src.auth.models import (
    UserCreate,
    Token,
    GoogleCodeAuth,  # заменил GoogleAuth
    GoogleLoginResponse,
    GoogleCallbackRequest,
    ProfileOut,
    TokensUserOut,
    UserRead,
    UserUpdate,
    LoginRequest,
    RefreshTokenRequest,
    EmailVerificationRequest,
    EmailVerificationResponse,
    VerifyEmailRequest,
    VerifyEmailResponse,
    RegistrationResponse,
    UserCreateGoogle,  # добавил новую модель
)
from src.auth.services import (
    get_user_by_email,
    get_pending_user_by_email,
    create_user_google,  # добавил импорт
    create_pending_user,
    authenticate_user,
    create_access_token,
    create_refresh_token,
    get_password_hash,
    cleanup_expired_pending_users,
)
from src.auth.email_service import (
    send_verification_email,
    send_verification_email_for_pending_user,
    verify_email_token,
    resend_verification_email,
)
from src.auth.security import (
    validate_registration_security,
    security_check_email_send,
    security_check_email_verify,
    get_client_ip,
    cleanup_rate_limits,
)
from src.database import get_async_db
from src.auth.schema import User, PendingUser, RateLimit
from src.auth.config import (
    GOOGLE_CLIENT_ID, 
    GOOGLE_CLIENT_SECRET, 
    GOOGLE_REDIRECT_URI, 
    GOOGLE_AUTH_ENDPOINT,
    GOOGLE_TOKEN_ENDPOINT,
    GOOGLE_USERINFO_ENDPOINT,
    GOOGLE_SCOPES,
    REFRESH_SECRET_KEY, 
    ALGORITHM
)
from src.auth.dependencies import get_current_user
from datetime import datetime
from sqlalchemy import select
import requests as sync_requests  # чтобы не конфликтовать с google.auth.transport.requests
import os

router = APIRouter(tags=["auth"])


@router.post("/register", response_model=RegistrationResponse)
async def register(
    user_in: UserCreate,
    request: Request,
    db: AsyncSession = Depends(get_async_db)
):
    """Register new user - creates pending user and sends verification email"""
    
    # Get client IP address
    ip_address = get_client_ip(request)
    
    # Cleanup expired records first
    await cleanup_expired_pending_users(db)
    await cleanup_rate_limits(db)
    
    # Security validation - ВРЕМЕННО ОТКЛЮЧЕНО ДЛЯ ТЕСТИРОВАНИЯ
    # security_ok, security_msg = await validate_registration_security(
    #     db, ip_address, user_in.email
    # )
    # if not security_ok:
    #     raise HTTPException(status_code=429, detail=security_msg)
    
    # Check if user already exists (confirmed users)
    existing_user = await get_user_by_email(db, user_in.email)
    if existing_user:
        raise HTTPException(
            status_code=422, 
            detail=[{
                "field": "email",
                "message": "Email address is already registered"
            }]
        )
    
    # Check if pending user already exists (unconfirmed users)
    existing_pending = await get_pending_user_by_email(db, user_in.email)
    if existing_pending:
        # Email is already taken by a pending user
        raise HTTPException(
            status_code=422, 
            detail=[{
                "field": "email",
                "message": "Email address is already registered"
            }]
        )
    
    # Create pending user with IP tracking
    pending_user = await create_pending_user(db, user_in)
    pending_user.ip_address = ip_address
    await db.commit()
    
    # Send verification email
    verification = await send_verification_email_for_pending_user(db, pending_user)
    
    if not verification:
        # If email fails, delete pending user
        await db.delete(pending_user)
        await db.commit()
        raise HTTPException(
            status_code=500, 
            detail="Не удалось отправить письмо с подтверждением. Попробуйте позже."
        )
    
    return RegistrationResponse(
        message="Регистрация почти завершена! Проверьте email для подтверждения.",
        email=user_in.email,
        verification_sent=True
    )


@router.post("/send-verification-email", response_model=EmailVerificationResponse)
async def send_verification_email_endpoint(
    request_data: EmailVerificationRequest,
    request: Request,
    db: AsyncSession = Depends(get_async_db)
):
    """Send or resend verification email"""
    
    # Get client IP address
    ip_address = get_client_ip(request)
    
    # Security check - ВРЕМЕННО ОТКЛЮЧЕНО ДЛЯ ТЕСТИРОВАНИЯ
    # security_ok, security_msg = await security_check_email_send(
    #     db, ip_address, request_data.email
    # )
    # if not security_ok:
    #     raise HTTPException(status_code=429, detail=security_msg)
    
    success, message = await resend_verification_email(db, request_data.email)
    
    if not success:
        raise HTTPException(status_code=400, detail=message)
    
    return EmailVerificationResponse(
        message=message,
        email=request_data.email
    )


@router.post("/verify-email", response_model=VerifyEmailResponse)
async def verify_email_endpoint(
    request_data: VerifyEmailRequest,
    request: Request,
    db: AsyncSession = Depends(get_async_db)
):
    """Verify email using token and create user account"""
    
    # Get client IP address
    ip_address = get_client_ip(request)
    
    # Security check - ВРЕМЕННО ОТКЛЮЧЕНО ДЛЯ ТЕСТИРОВАНИЯ
    # security_ok, security_msg = await security_check_email_verify(db, ip_address)
    # if not security_ok:
    #     raise HTTPException(status_code=429, detail=security_msg)
    
    success, message, user = await verify_email_token(db, request_data.token)
    
    if not success:
        raise HTTPException(status_code=400, detail=message)
    
    # If user was just created, return tokens for automatic login
    tokens = None
    if user and success:
        access_token = await create_access_token({"sub": user.email})
        refresh_token = await create_refresh_token({"sub": user.email})
        tokens = Token(access_token=access_token, refresh_token=refresh_token)
    
    return VerifyEmailResponse(
        message=message,
        is_verified=user.is_verified if user else False,
        tokens=tokens
    )


@router.post("/login", response_model=Token)
async def login(
    form_data: LoginRequest, 
    request: Request,
    db: AsyncSession = Depends(get_async_db)
):
    """Login with email and password"""
    
    # Check if it's a pending user first
    pending_user = await get_pending_user_by_email(db, form_data.email)
    if pending_user:
        raise HTTPException(
            status_code=400,
            detail="Аккаунт не подтвержден. Проверьте email для завершения регистрации."
        )
    
    user = await authenticate_user(db, form_data.email, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный email или пароль",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Optional: Check if email is verified
    if not user.is_verified:
        # Allow login but user will see unverified status
        pass
    
    access_token = await create_access_token({"sub": user.email})
    refresh_token = await create_refresh_token({"sub": user.email})
    return {"access_token": access_token, "refresh_token": refresh_token}


@router.post("/google", response_model=Token)
async def google_auth(
    payload: GoogleCodeAuth,
    request: Request,
    db: AsyncSession = Depends(get_async_db)
):
    """Authenticate user via Google OAuth2 code flow"""
    try:
        code = payload.code
        if not code:
            raise HTTPException(status_code=400, detail="No code provided")

        # 1. Обменять code на id_token
        token_url = "https://oauth2.googleapis.com/token"
        data = {
            "code": code,
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "redirect_uri": payload.redirect_uri,
            "grant_type": "authorization_code"
        }
        resp = sync_requests.post(token_url, data=data)
        if not resp.ok:
            raise HTTPException(status_code=400, detail=f"Google token exchange failed: {resp.text}")
        tokens = resp.json()
        id_token_str = tokens.get("id_token")
        if not id_token_str:
            raise HTTPException(status_code=400, detail="No id_token in Google response")

        # 2. Проверить id_token и дальше по старой логике
        id_info = id_token.verify_oauth2_token(
            id_token_str, requests.Request(), GOOGLE_CLIENT_ID
        )
        if not id_info:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid Google ID token"
            )
        email = id_info.get("email")
        name = id_info.get("name")
        if not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email not found in Google ID token"
            )
        existing_user = await get_user_by_email(db, email)
        if not existing_user:
            new_user = await create_user_google(db, UserCreateGoogle(email=email, full_name=name or email.split("@")[0]))
            await db.commit()
            user = new_user
        else:
            user = existing_user
        access_token = await create_access_token({"sub": user.email})
        refresh_token = await create_refresh_token({"sub": user.email})
        return Token(access_token=access_token, refresh_token=refresh_token)
    except Exception as e:
        import traceback
        print("[GOOGLE AUTH ERROR]", traceback.format_exc())
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Google authentication failed: {str(e)}"
        )


@router.get("/google/login", response_model=GoogleLoginResponse)
async def google_login():
    """Generate Google OAuth 2.0 authorization URL"""
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "response_type": "code",
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "scope": " ".join(GOOGLE_SCOPES),
        "access_type": "offline",
        "prompt": "consent",
    }
    url = f"{GOOGLE_AUTH_ENDPOINT}?{urlencode(params)}"
    return GoogleLoginResponse(auth_url=url)


@router.post("/google/callback", response_model=TokensUserOut)
async def google_callback(
    payload: GoogleCallbackRequest,
    db: AsyncSession = Depends(get_async_db)
):
    """Handle Google OAuth 2.0 callback with authorization code"""
    if not payload.code:
        raise HTTPException(status_code=400, detail="Code not provided")

    try:
        async with httpx.AsyncClient() as client:
            # Exchange authorization code for access token
            token_data = {
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "code": payload.code,
                "grant_type": "authorization_code",
                "redirect_uri": GOOGLE_REDIRECT_URI,
            }
            
            token_resp = await client.post(GOOGLE_TOKEN_ENDPOINT, data=token_data)
            if token_resp.status_code != 200:
                raise HTTPException(status_code=400, detail="Failed to exchange code for token")
            
            token_info = token_resp.json()
            access_token = token_info.get("access_token")
            
            if not access_token:
                raise HTTPException(status_code=400, detail="No access token received")
            
            # Get user info using the access token
            headers = {"Authorization": f"Bearer {access_token}"}
            resp = await client.get(GOOGLE_USERINFO_ENDPOINT, headers=headers, params={"alt": "json"})
        
        if resp.status_code != 200:
            raise HTTPException(status_code=400, detail="Could not fetch user info from Google")

        data = resp.json()
        email = data.get("email")
        if not email:
            raise HTTPException(status_code=400, detail="Email not available")

        picture = data.get("picture")
        given_name = data.get("given_name")
        family_name = data.get("family_name")
        name = data.get("name")

        # Find existing user
        existing_user = await get_user_by_email(db, email.lower())
        
        if existing_user is None:
            # Create new user
            random_password = get_password_hash(access_token)
            user = User(
                email=email.lower(),
                hashed_password=random_password,
                full_name=name or f"{given_name or ''} {family_name or ''}".strip(),
                avatar=picture,
                first_name=given_name,
                last_name=family_name,
                is_verified=True,
                is_active=True
            )
            db.add(user)
            await db.commit()
            await db.refresh(user)
        else:
            user = existing_user
            # Update user fields if they're empty
            updated = False
            if picture and not user.avatar:
                user.avatar = picture
                updated = True
            if given_name and not user.first_name:
                user.first_name = given_name
                updated = True
            if family_name and not user.last_name:
                user.last_name = family_name
                updated = True
            if updated:
                db.add(user)
                await db.commit()
                await db.refresh(user)

        # Generate JWT tokens
        access_token = await create_access_token({"sub": str(user.id)})
        refresh_token = await create_refresh_token({"sub": str(user.id)})
        
        return TokensUserOut(
            access_token=access_token, 
            refresh_token=refresh_token, 
            user=ProfileOut.from_orm(user)
        )

    except Exception as e:
        import traceback
        print("[GOOGLE CALLBACK ERROR]", traceback.format_exc())
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Google callback failed: {str(e)}"
        )

@router.post("/refresh", response_model=Token)
async def refresh_access_token(
    request: RefreshTokenRequest, db: AsyncSession = Depends(get_async_db)
):
    print("--- REFRESHING TOKEN ---")
    try:
        payload = jwt.decode(
            request.refresh_token, REFRESH_SECRET_KEY, algorithms=[ALGORITHM]
        )
        email: str = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=401, detail="Invalid refresh token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    user = await get_user_by_email(db, email)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    access_token = await create_access_token({"sub": user.email})
    refresh_token = await create_refresh_token({"sub": user.email})
    return {"access_token": access_token, "refresh_token": refresh_token}


@router.get("/me", response_model=UserRead)
async def get_current_user_profile(
    current_user: User = Depends(get_current_user)
):
    """Get current user's profile - secure way without needing user ID"""
    return current_user

@router.put("/me", response_model=UserRead)
async def update_current_user_profile(
    user_up: UserUpdate,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """Update current user's profile - secure way without needing user ID"""
    for var, value in user_up.dict(exclude_unset=True).items():
        setattr(current_user, var, value)
    db.add(current_user)
    await db.commit()
    await db.refresh(current_user)
    return current_user

@router.delete("/me")
async def delete_current_user_account(
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """Delete current user's account - secure way without needing user ID"""
    await db.delete(current_user)
    await db.commit()
    return {"detail": "Your account has been deleted"}

@router.get("/users/{user_id}", response_model=UserRead)
async def read_user(
    user_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.id != user_id:
        raise HTTPException(
            status_code=403, 
            detail="You can only access your own profile"
        )
    
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@router.put("/users/{user_id}", response_model=UserRead)
async def update_user(
    user_id: int,
    user_up: UserUpdate,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.id != user_id:
        raise HTTPException(
            status_code=403, 
            detail="You can only update your own profile"
        )
    
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
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.id != user_id:
        raise HTTPException(
            status_code=403, 
            detail="You can only delete your own account"
        )
    
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    await db.delete(user)
    await db.commit()
    return {"detail": "User deleted successfully"}


# Admin endpoint for monitoring (optional)
@router.get("/admin/security-stats")
async def get_security_stats(
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user)
):
    """Get security statistics (admin only)"""
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Count pending users
    from sqlalchemy import func as sql_func
    pending_count = await db.execute(
        select(sql_func.count(PendingUser.id))
    )
    
    # Count rate limit records  
    rate_limit_count = await db.execute(
        select(sql_func.count(RateLimit.id))
    )
    
    return {
        "pending_users": pending_count.scalar(),
        "active_rate_limits": rate_limit_count.scalar(),
        "max_pending_per_ip": 3,
        "rate_limits": {
            "register": "3 requests per hour",
            "send_verification": "5 requests per 30 minutes", 
            "verify_email": "10 requests per 15 minutes"
        }
    }

@router.post("/test-email")
async def test_email_sending(
    email: str = Body(..., embed=True),
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
):
    """Test email sending functionality (development only)"""
    # Only allow superusers to test email
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    from src.auth.email_service import send_email
    
    html_content = """
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2 style="color: #4F46E5;">🎯 Тестовое письмо от Reeply</h2>
        <p>Если вы получили это письмо, значит email настроен правильно!</p>
        <p>ZeptoMail API работает корректно. ✅</p>
        <p><small>Время отправки: {datetime.now()}</small></p>
    </div>
    """
    
    try:
        success = await send_email(
            to_email=email,
            subject="🎯 Тест email от Reeply",
            html_content=html_content
        )
        
        if success:
            return {"message": "Тестовое письмо отправлено успешно!", "success": True}
        else:
            return {"message": "Ошибка при отправке письма", "success": False}
            
    except Exception as e:
        return {"message": f"Ошибка: {str(e)}", "success": False}