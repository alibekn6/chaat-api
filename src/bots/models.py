from pydantic import BaseModel
from typing import List, Optional
from uuid import UUID
from src.bots.schema import KnowledgeSourceType


# Schemas for KnowledgeSource
class KnowledgeSourceBase(BaseModel):
    source_type: KnowledgeSourceType
    content: Optional[str] = None
    url: Optional[str] = None
    file_path: Optional[str] = None


class KnowledgeSourceCreate(KnowledgeSourceBase):
    pass


class KnowledgeSource(KnowledgeSourceBase):
    id: int
    bot_id: int

    class Config:
        from_attributes = True


class BotBase(BaseModel):
    name: str
    description: Optional[str] = None
    bot_name: Optional[str] = None
    bot_greeting: Optional[str] = None
    bot_tonality: Optional[str] = None


class BotUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    bot_name: Optional[str] = None
    bot_greeting: Optional[str] = None
    bot_tonality: Optional[str] = None


class BotCreate(BotBase):
    pass


class Bot(BotBase):
    id: int
    owner_id: int
    link: UUID
    knowledge_sources: List[KnowledgeSource] = []

    class Config:
        from_attributes = True 