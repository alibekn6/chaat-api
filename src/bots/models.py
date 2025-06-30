from pydantic import BaseModel, Field
from typing import List, Optional
from uuid import UUID
from datetime import datetime
from enum import Enum


class BotType(str, Enum):
    simple_chat = "simple_chat"
    qa_knowledge_base = "qa_knowledge_base"


class BotBase(BaseModel):
    bot_name: str
    requirements: str
    bot_token: str = Field(..., description="The Telegram bot token.")
    bot_type: BotType = BotType.simple_chat


class BotCreate(BotBase):
    pass


class BotUpdate(BaseModel):
    bot_name: Optional[str] = None
    requirements: Optional[str] = None
    bot_token: Optional[str] = None
    bot_type: Optional[BotType] = None



class Bot(BotBase):
    id: int
    owner_id: int
    generated_code: Optional[str] = None
    status: str
    is_running: bool
    created_at: datetime
    pid: Optional[int] = None
    knowledge_base_status: str = "empty"  # empty, processing, ready, failed

    class Config:
        from_attributes = True 