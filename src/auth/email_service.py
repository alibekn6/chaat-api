import smtplib
import secrets
import aiohttp
import json
from datetime import datetime, timedelta, timezone
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, Union
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from src.auth.config import (
    SMTP_SERVER,
    SMTP_PORT,
    SMTP_USERNAME,
    SMTP_PASSWORD,
    EMAIL_FROM,
    EMAIL_FROM_NAME,
    EMAIL_VERIFICATION_EXPIRE_HOURS,
    FRONTEND_URL,
    ZEPTOMAIL_API_KEY,
    ZEPTOMAIL_DOMAIN,
    USE_ZEPTOMAIL,
)
from src.auth.schema import EmailVerification, User, PendingUser


def generate_verification_token() -> str:
    """Generate a secure verification token"""
    return secrets.token_urlsafe(32)


def create_verification_email_html(verification_url: str, user_name: str = "") -> str:
    """Create HTML email template for verification"""
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500&display=swap');
            
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}
            
            body {{
                font-family: 'JetBrains Mono', monospace;
                background-color: #ffffff;
                color: #000000;
                line-height: 1.6;
            }}
            
            .container {{ 
                max-width: 500px; 
                margin: 40px auto; 
                padding: 0 20px;
            }}
            
            .header {{ 
                text-align: center; 
                margin-bottom: 40px;
                border-bottom: 1px solid #000000;
                padding-bottom: 20px;
            }}
            
            .header h1 {{
                font-size: 18px;
                font-weight: 500;
                letter-spacing: 0.5px;
                margin: 0;
            }}
            
            .content {{ 
                margin-bottom: 40px;
            }}
            
            .content h2 {{
                font-size: 16px;
                font-weight: 500;
                margin-bottom: 20px;
            }}
            
            .content p {{
                font-size: 14px;
                margin-bottom: 16px;
                line-height: 1.5;
            }}
            
            .button {{ 
                display: inline-block; 
                background-color: #ffffff; 
                color: #000000 !important; 
                padding: 12px 24px; 
                text-decoration: none !important; 
                border: 1px solid #000000;
                font-family: 'JetBrains Mono', monospace;
                font-size: 14px;
                font-weight: 500;
                letter-spacing: 0.3px;
                transition: all 0.2s ease;
            }}
            
            .button:hover {{
                background-color: #000000;
                color: #ffffff !important;
            }}
            
            .button:visited {{
                color: #000000 !important;
            }}
            
            .button:active {{
                color: #000000 !important;
            }}
            
            .button-container {{
                text-align: center;
                margin: 30px 0;
            }}
            
            .url-box {{
                background-color: #f8f8f8;
                border: 1px solid #e0e0e0;
                padding: 12px;
                font-size: 12px;
                word-break: break-all;
                margin: 16px 0;
                font-family: 'JetBrains Mono', monospace;
            }}
            
            .footer {{ 
                text-align: center; 
                color: #666666; 
                font-size: 12px;
                border-top: 1px solid #e0e0e0;
                padding-top: 20px;
            }}
            
            .footer p {{
                margin-bottom: 8px;
            }}
            
            .warning {{
                background-color: #f8f8f8;
                border-left: 3px solid #000000;
                padding: 12px;
                margin: 20px 0;
                font-size: 13px;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>EMAIL VERIFICATION</h1>
            </div>
            
            <div class="content">
                <h2>Welcome{', ' + user_name if user_name else ''}.</h2>
                
                <p>Please verify your email address to complete registration.</p>
                
                <div class="warning">
                    <strong>IMPORTANT:</strong> Your account will be created only after email verification.
                </div>
                
                <div class="button-container">
                    <a href="{verification_url}" class="button">VERIFY EMAIL</a>
                </div>
                
                <p><strong>Or copy this link:</strong></p>
                <div class="url-box">{verification_url}</div>
                
                <p>Link expires in {EMAIL_VERIFICATION_EXPIRE_HOURS} hours.</p>
            </div>
            
            <div class="footer">
                <p>If you didn't register, ignore this email.</p>
                <p>© 2025 Chaat. All rights reserved.</p>
            </div>
        </div>
    </body>
    </html>
    """


async def send_email_via_zeptomail(
    to_email: str,
    subject: str,
    html_content: str,
    to_name: str = ""
) -> bool:
    """Send email via ZeptoMail API"""
    
    
    if not ZEPTOMAIL_API_KEY:
        print("❌ ZeptoMail API key not configured")
        return False
    
    url = "https://api.zeptomail.com/v1.1/email"
    
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": f"Zoho-enczapikey {ZEPTOMAIL_API_KEY}"
    }
    
    payload = {
        "from": {
            "address": EMAIL_FROM,
            "name": EMAIL_FROM_NAME
        },
        "to": [{
            "email_address": {
                "address": to_email,
                "name": to_name
            }
        }],
        "subject": subject,
        "htmlbody": html_content
    }
    
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload) as response:
                response_text = await response.text()
                
                if response.status in [200, 201]:  # ZeptoMail returns 201 for successful requests
                    result = await response.json()
                    print(f"✅ ZeptoMail email sent successfully to {to_email}")
                    return True
                else:
                    print(f"❌ ZeptoMail API error: {response.status} - {response_text}")
                    return False
                    
    except Exception as e:
        print(f"❌ Failed to send email via ZeptoMail: {e}")
        import traceback
        return False


async def send_email_via_smtp(
    to_email: str,
    subject: str,
    html_content: str,
    to_name: str = ""
) -> bool:
    """Send email via SMTP (fallback method)"""
    
    if not SMTP_USERNAME or not SMTP_PASSWORD:
        print("SMTP credentials not configured")
        return False
    
    try:
        # Create email
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{EMAIL_FROM_NAME} <{EMAIL_FROM}>"
        msg["To"] = to_email
        
        # Add HTML content
        html_part = MIMEText(html_content, "html")
        msg.attach(html_part)
        
        # Send email
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.send_message(msg)
        
        print(f"SMTP email sent successfully to {to_email}")
        return True
        
    except Exception as e:
        print(f"Failed to send email via SMTP: {e}")
        return False


async def send_email(
    to_email: str,
    subject: str,
    html_content: str,
    to_name: str = ""
) -> bool:
    """Send email using configured method (ZeptoMail or SMTP)"""
    
    if USE_ZEPTOMAIL:
        # Try ZeptoMail first
        success = await send_email_via_zeptomail(to_email, subject, html_content, to_name)
        if success:
            return True
        
        # Fallback to SMTP if ZeptoMail fails
        print("ZeptoMail failed, trying SMTP fallback...")
        return await send_email_via_smtp(to_email, subject, html_content, to_name)
    else:
        # Use SMTP directly
        return await send_email_via_smtp(to_email, subject, html_content, to_name)


async def send_verification_email_for_pending_user(
    db: AsyncSession,
    pending_user: PendingUser,
    background_tasks=None
) -> Optional[EmailVerification]:
    """Send verification email for pending user"""
    
    # Creating email verification record
    
    # Generate verification token
    token = generate_verification_token()
    expires_at = datetime.now(timezone.utc) + timedelta(hours=EMAIL_VERIFICATION_EXPIRE_HOURS)
    
    
    # Create verification record for pending user
    verification = EmailVerification(
        pending_user_id=pending_user.id,
        verification_token=token,
        expires_at=expires_at
    )
    
    
    db.add(verification)
    await db.commit()
    await db.refresh(verification)
    
    
    # Create verification URL
    verification_url = f"{FRONTEND_URL}/verify-email?token={token}"
    
    # Create email content
    subject = f"Email Verification - {EMAIL_FROM_NAME}"
    html_content = create_verification_email_html(verification_url, pending_user.full_name or "")
    
    # Send email
    success = await send_email(
        to_email=pending_user.email,
        subject=subject,
        html_content=html_content,
        to_name=pending_user.full_name or ""
    )
    
    if success:
        print(f"Verification email sent to {pending_user.email}")
        return verification
    else:
        # Delete verification record if email failed
        await db.delete(verification)
        await db.commit()
        return None


async def send_verification_email(
    db: AsyncSession,
    user: User,
    background_tasks=None
) -> Optional[EmailVerification]:
    """Send verification email to existing user (for resend functionality)"""
    
    # Generate verification token
    token = generate_verification_token()
    expires_at = datetime.now(timezone.utc) + timedelta(hours=EMAIL_VERIFICATION_EXPIRE_HOURS)
    
    # Create verification record
    verification = EmailVerification(
        user_id=user.id,
        verification_token=token,
        expires_at=expires_at
    )
    db.add(verification)
    await db.commit()
    await db.refresh(verification)
    
    # Create verification URL
    verification_url = f"{FRONTEND_URL}/verify-email?token={token}"
    
    # Create email content
    subject = f"Email Verification - {EMAIL_FROM_NAME}"
    html_content = create_verification_email_html(verification_url, user.full_name or "")
    
    # Send email
    success = await send_email(
        to_email=user.email,
        subject=subject,
        html_content=html_content,
        to_name=user.full_name or ""
    )
    
    if success:
        print(f"Verification email sent to {user.email}")
        return verification
    else:
        # Delete verification record if email failed
        await db.delete(verification)
        await db.commit()
        return None


async def verify_email_token(db: AsyncSession, token: str) -> tuple[bool, str, Optional[User]]:
    """Verify email token and create user account from pending user"""
    

    result = await db.execute(
        select(EmailVerification).where(
            EmailVerification.verification_token == token,
            EmailVerification.is_used == False,
            EmailVerification.expires_at > datetime.now(timezone.utc),
            EmailVerification.pending_user_id.isnot(None)
        )
    )
    verification = result.scalars().first()
    
    if verification:
        # Found verification for pending user
        pending_user_result = await db.execute(
            select(PendingUser).where(PendingUser.id == verification.pending_user_id)
        )
        pending_user = pending_user_result.scalars().first()
        
        if not pending_user:
            return False, "Данные регистрации не найдены", None
        
        # Check if user with this email already exists
        existing_user_result = await db.execute(select(User).where(User.email == pending_user.email))
        existing_user = existing_user_result.scalars().first()
        
        if existing_user:
            # Clean up pending user and verification
            await db.delete(verification)
            await db.delete(pending_user)
            await db.commit()
            return False, "Пользователь с таким email уже существует", None
        
        
        user = User(
            email=pending_user.email,
            hashed_password=pending_user.hashed_password,
            full_name=pending_user.full_name,
            is_verified=True,
            is_active=True
        )
        db.add(user)
        
        await db.commit()
        await db.refresh(user)
        
        verification.is_used = True
        verification.user_id = user.id  # Link to created user
        
        await db.delete(pending_user)
        
        await db.commit()
        
        return True, "Email подтвержден! Аккаунт успешно создан!", user
    
    result = await db.execute(
        select(EmailVerification).where(
            EmailVerification.verification_token == token,
            EmailVerification.is_used == False,
            EmailVerification.expires_at > datetime.now(timezone.utc),
            EmailVerification.user_id.isnot(None)
        )
    )
    verification = result.scalars().first()
    
    if not verification:
        return False, "Неверный или истекший токен", None
    
    # Get user
    user_result = await db.execute(select(User).where(User.id == verification.user_id))
    user = user_result.scalars().first()
    
    if not user:
        return False, "Пользователь не найден", None
    
    if user.is_verified:
        return True, "Email уже подтвержден", user
    
    # Mark verification as used and user as verified
    verification.is_used = True
    user.is_verified = True
    
    await db.commit()
    await db.refresh(user)
    
    return True, "Email успешно подтвержден!", user


async def resend_verification_email(db: AsyncSession, email: str) -> tuple[bool, str]:
    """Resend verification email"""
    

    pending_result = await db.execute(select(PendingUser).where(PendingUser.email == email))
    pending_user = pending_result.scalars().first()
    
    if pending_user:
        # Check rate limiting for pending user
        recent_verification = await db.execute(
            select(EmailVerification).where(
                EmailVerification.pending_user_id == pending_user.id,
                EmailVerification.created_at > datetime.now(timezone.utc) - timedelta(minutes=5)
            )
        )
        
        if recent_verification.scalars().first():
            return False, "Письмо уже отправлено. Подождите 5 минут перед повторной отправкой"
        
        # Send verification email for pending user
        verification = await send_verification_email_for_pending_user(db, pending_user)
        
        if verification:
            return True, "Письмо с подтверждением отправлено для завершения регистрации"
        else:
            return False, "Ошибка отправки email"
    
    # Find existing user
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalars().first()
    
    if not user:
        return False, "Пользователь с таким email не найден"
    
    if user.is_verified:
        return False, "Email уже подтвержден"
    
    # Check if there's a recent verification email (rate limiting)
    recent_verification = await db.execute(
        select(EmailVerification).where(
            EmailVerification.user_id == user.id,
            EmailVerification.created_at > datetime.now(timezone.utc) - timedelta(minutes=5)
        )
    )
    
    if recent_verification.scalars().first():
        return False, "Письмо уже отправлено. Подождите 5 минут перед повторной отправкой"
    
    # Send new verification email
    verification = await send_verification_email(db, user)
    
    if verification:
        return True, "Письмо с подтверждением отправлено"
    else:
        return False, "Ошибка отправки email" 