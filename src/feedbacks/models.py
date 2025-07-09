from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    ForeignKey,
    BigInteger,
    DateTime,
    func,
)
from sqlalchemy.orm import relationship
from src.database import Base


class Feedback(Base):
    """Model for storing user feedback/reviews."""
    __tablename__ = "feedbacks"

    id = Column(Integer, primary_key=True, index=True)
    bot_id = Column(Integer, ForeignKey("bots.id"), nullable=False)
    
    # Telegram user info
    user_telegram_id = Column(BigInteger, nullable=False)
    username = Column(String(255), nullable=True)
    first_name = Column(String(255), nullable=True)
    last_name = Column(String(255), nullable=True)
    
    # Feedback content
    message_text = Column(Text, nullable=True)
    rating = Column(Integer, nullable=True)  # 1-5 stars
    category = Column(String(100), nullable=True)
    
    # Status tracking
    status = Column(String(50), default="new")  # new, read, replied, archived
    created_at = Column(DateTime, default=func.now())
    
    # Relationships
    bot = relationship("Bot", back_populates="feedbacks")
    images = relationship("FeedbackImage", back_populates="feedback", cascade="all, delete-orphan")


class FeedbackImage(Base):
    """Model for storing images attached to feedback."""
    __tablename__ = "feedback_images"

    id = Column(Integer, primary_key=True, index=True)
    feedback_id = Column(Integer, ForeignKey("feedbacks.id"), nullable=False)
    
    # File info
    file_id = Column(String(255), nullable=True)  # Telegram file ID (optional now)
    file_path = Column(String(500), nullable=False)  # Azure URL or local path
    storage_type = Column(String(20), default="azure")  # azure, local, telegram
    file_size = Column(Integer, nullable=True)
    original_filename = Column(String(255), nullable=True)  # Original filename
    created_at = Column(DateTime, default=func.now())
    
    # Relationships
    feedback = relationship("Feedback", back_populates="images") 