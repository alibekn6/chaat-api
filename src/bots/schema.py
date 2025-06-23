import uuid
from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    Enum as SQLAlchemyEnum,
    ForeignKey,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from src.database import Base
import enum


class Bot(Base):
    __tablename__ = "bots"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    description = Column(Text)
    bot_name = Column(String)
    bot_greeting = Column(Text)
    bot_tonality = Column(String)
    link = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, nullable=False)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    owner = relationship("User", back_populates="bots")
    knowledge_sources = relationship(
        "KnowledgeSource",
        back_populates="bot",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class KnowledgeSourceType(str, enum.Enum):
    text = "text"
    url = "url"
    file = "file"


class KnowledgeSource(Base):
    __tablename__ = "knowledge_sources"

    id = Column(Integer, primary_key=True, index=True)
    bot_id = Column(Integer, ForeignKey("bots.id"), nullable=False)
    source_type = Column(SQLAlchemyEnum(KnowledgeSourceType), nullable=False)
    content = Column(Text)  # for text
    url = Column(String)  # for url
    file_path = Column(String)  # for file

    bot = relationship("Bot", back_populates="knowledge_sources") 