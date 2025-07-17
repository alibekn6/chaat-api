from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from src.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    is_superuser = Column(Boolean, default=False)
    google_id = Column(String, unique=True, index=True, nullable=True)

    bots = relationship("Bot", back_populates="owner")
    email_verifications = relationship("EmailVerification", back_populates="user", cascade="all, delete-orphan")


class EmailVerification(Base):
    __tablename__ = "email_verifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # Nullable for pending users
    pending_user_id = Column(Integer, ForeignKey("pending_users.id"), nullable=True)
    verification_token = Column(String, unique=True, index=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=False)
    is_used = Column(Boolean, default=False)

    user = relationship("User", back_populates="email_verifications")
    pending_user = relationship("PendingUser", back_populates="email_verification")


class PendingUser(Base):
    __tablename__ = "pending_users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=False)  # Auto-cleanup
    ip_address = Column(String, nullable=True)  # Track IP for rate limiting

    email_verification = relationship("EmailVerification", back_populates="pending_user", uselist=False)


class RateLimit(Base):
    __tablename__ = "rate_limits"

    id = Column(Integer, primary_key=True, index=True)
    ip_address = Column(String, index=True, nullable=False)
    endpoint = Column(String, nullable=False)  # e.g., "register", "send_verification"
    request_count = Column(Integer, default=1)
    window_start = Column(DateTime(timezone=True), server_default=func.now())
    last_request = Column(DateTime(timezone=True), server_default=func.now())
