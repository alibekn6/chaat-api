from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from enum import Enum


class FeedbackStatus(str, Enum):
    new = "new"
    read = "read"
    replied = "replied"
    archived = "archived"


class FeedbackImageBase(BaseModel):
    file_path: str
    storage_type: Optional[str] = "azure"  # azure, local, telegram
    file_id: Optional[str] = None  # Telegram file ID (optional)
    file_size: Optional[int] = None
    original_filename: Optional[str] = None


class FeedbackImageCreate(FeedbackImageBase):
    pass


class FeedbackImage(FeedbackImageBase):
    id: int
    feedback_id: int
    created_at: datetime

    class Config:
        from_attributes = True


class FeedbackBase(BaseModel):
    message_text: Optional[str] = None
    rating: Optional[int] = Field(None, ge=1, le=5, description="Rating from 1 to 5 stars")
    category: Optional[str] = None


class FeedbackCreate(FeedbackBase):
    user_telegram_id: int
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    images: Optional[List[FeedbackImageCreate]] = []


class FeedbackUpdate(BaseModel):
    status: Optional[FeedbackStatus] = None
    category: Optional[str] = None


class FeedbackStatusUpdate(BaseModel):
    status: FeedbackStatus


class Feedback(FeedbackBase):
    id: int
    bot_id: int
    user_telegram_id: int
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    status: FeedbackStatus
    created_at: datetime
    images: List[FeedbackImage] = []

    class Config:
        from_attributes = True


class FeedbackResponse(FeedbackBase):
    id: int
    bot_id: int
    user_telegram_id: int
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    status: FeedbackStatus
    created_at: datetime
    images: List[FeedbackImage] = []

    class Config:
        from_attributes = True


class FeedbackStats(BaseModel):
    total_count: int
    average_rating: float
    new_count: int
    read_count: int
    replied_count: int 