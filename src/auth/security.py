import re
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import and_, or_
from src.auth.schema import RateLimit, PendingUser
from src.auth.config import EMAIL_VERIFICATION_EXPIRE_HOURS

# Rate limiting configuration
RATE_LIMIT_CONFIG = {
    "register": {
        "max_requests": 3,  # Maximum 3 registration attempts
        "window_minutes": 60,  # Per hour
    },
    "send_verification": {
        "max_requests": 5,  # Maximum 5 email sends
        "window_minutes": 30,  # Per 30 minutes
    },
    "verify_email": {
        "max_requests": 10,  # Maximum 10 verification attempts
        "window_minutes": 15,  # Per 15 minutes
    }
}

# Maximum pending users per IP
MAX_PENDING_USERS_PER_IP = 3


def is_valid_email_format(email: str) -> bool:
    """Basic email format validation"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def is_disposable_email(email: str) -> bool:
    """Check if email is from a disposable email service"""
    disposable_domains = {
        "10minutemail.com", "guerrillamail.com", "mailinator.com",
        "tempmail.org", "yopmail.com", "trash-mail.com",
        "temp-mail.org", "throwaway.email", "mohmal.com"
    }
    
    domain = email.split('@')[-1].lower()
    return domain in disposable_domains


async def check_rate_limit(
    db: AsyncSession, 
    ip_address: str, 
    endpoint: str
) -> Tuple[bool, str]:
    """Check if IP address has exceeded rate limit for endpoint"""
    
    config = RATE_LIMIT_CONFIG.get(endpoint)
    if not config:
        return True, ""  # No rate limit configured
    
    max_requests = config["max_requests"]
    window_minutes = config["window_minutes"]
    window_start = datetime.now(timezone.utc) - timedelta(minutes=window_minutes)
    
    # Find existing rate limit record
    result = await db.execute(
        select(RateLimit).where(
            and_(
                RateLimit.ip_address == ip_address,
                RateLimit.endpoint == endpoint,
                RateLimit.window_start > window_start
            )
        )
    )
    rate_limit = result.scalars().first()
    
    if not rate_limit:
        # Create new rate limit record
        rate_limit = RateLimit(
            ip_address=ip_address,
            endpoint=endpoint,
            request_count=1
        )
        db.add(rate_limit)
        await db.commit()
        return True, ""
    
    # Check if within rate limit
    if rate_limit.request_count >= max_requests:
        time_remaining = (rate_limit.window_start + timedelta(minutes=window_minutes) - datetime.now(timezone.utc)).total_seconds()
        minutes_remaining = max(1, int(time_remaining / 60))
        return False, f"Превышен лимит запросов. Попробуйте через {minutes_remaining} минут."
    
    # Increment counter
    rate_limit.request_count += 1
    rate_limit.last_request = datetime.now(timezone.utc)
    await db.commit()
    
    return True, ""


async def check_pending_users_limit(db: AsyncSession, ip_address: str) -> Tuple[bool, str]:
    """Check if IP has too many pending users"""
    
    result = await db.execute(
        select(PendingUser).where(
            and_(
                PendingUser.ip_address == ip_address,
                PendingUser.expires_at > datetime.now(timezone.utc)
            )
        )
    )
    pending_users = result.scalars().all()
    
    if len(pending_users) >= MAX_PENDING_USERS_PER_IP:
        return False, f"Слишком много неподтвержденных регистраций с вашего IP. Максимум: {MAX_PENDING_USERS_PER_IP}"
    
    return True, ""


async def cleanup_rate_limits(db: AsyncSession) -> int:
    """Clean up old rate limit records"""
    cutoff_time = datetime.now(timezone.utc) - timedelta(hours=24)
    
    result = await db.execute(
        select(RateLimit).where(RateLimit.window_start < cutoff_time)
    )
    old_records = result.scalars().all()
    
    count = 0
    for record in old_records:
        await db.delete(record)
        count += 1
    
    if count > 0:
        await db.commit()
        print(f"Cleaned up {count} old rate limit records")
    
    return count


async def validate_registration_security(
    db: AsyncSession,
    ip_address: str,
    email: str
) -> Tuple[bool, str]:
    """Comprehensive security validation for registration"""
    
    # 1. Basic email format validation
    if not is_valid_email_format(email):
        return False, "Неверный формат email адреса"
    
    # 2. Check for disposable email
    if is_disposable_email(email):
        return False, "Временные email адреса не разрешены"
    
    # 3. Check rate limiting
    rate_ok, rate_msg = await check_rate_limit(db, ip_address, "register")
    if not rate_ok:
        return False, rate_msg
    
    # 4. Check pending users limit
    pending_ok, pending_msg = await check_pending_users_limit(db, ip_address)
    if not pending_ok:
        return False, pending_msg
    
    return True, ""


def get_client_ip(request) -> str:
    """Extract client IP address from request"""
    # Check for forwarded IP first (behind proxy/load balancer)
    if hasattr(request, 'headers'):
        forwarded = request.headers.get('X-Forwarded-For')
        if forwarded:
            return forwarded.split(',')[0].strip()
        
        real_ip = request.headers.get('X-Real-IP')
        if real_ip:
            return real_ip
    
    # Fallback to client host
    if hasattr(request, 'client') and request.client:
        return request.client.host
    
    return "unknown"


# Security middleware functions
async def security_check_email_send(
    db: AsyncSession,
    ip_address: str,
    email: str
) -> Tuple[bool, str]:
    """Security check for email sending operations"""
    
    # Rate limit check
    rate_ok, rate_msg = await check_rate_limit(db, ip_address, "send_verification")
    if not rate_ok:
        return False, rate_msg
    
    # Basic email validation
    if not is_valid_email_format(email):
        return False, "Неверный формат email адреса"
    
    return True, ""


async def security_check_email_verify(
    db: AsyncSession,
    ip_address: str
) -> Tuple[bool, str]:
    """Security check for email verification operations"""
    
    # Rate limit check
    rate_ok, rate_msg = await check_rate_limit(db, ip_address, "verify_email")
    if not rate_ok:
        return False, rate_msg
    
    return True, "" 