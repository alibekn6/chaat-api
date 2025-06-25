from pydantic import BaseModel, Field
from typing import List, Optional
from uuid import UUID
from datetime import datetime


class BotBase(BaseModel):
    bot_name: str
    requirements: str
    bot_token: str = Field(..., description="The Telegram bot token.")


class BotCreate(BotBase):
    pass


class BotUpdate(BaseModel):
    bot_name: Optional[str] = None
    requirements: Optional[str] = None
    bot_token: Optional[str] = None


class Bot(BotBase):
    id: int
    owner_id: int
    generated_code: Optional[str] = None
    status: str
    is_running: bool
    created_at: datetime
    pid: Optional[int] = None

    class Config:
        from_attributes = True 