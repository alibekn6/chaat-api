from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    ForeignKey,
    Boolean,
    DateTime,
    func,
)
from sqlalchemy.orm import relationship
from src.database import Base


class Bot(Base):
    __tablename__ = "bots"

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    bot_name = Column(String(255))
    bot_token = Column(String(255))  # This should be encrypted in a real app
    requirements = Column(Text, nullable=True)
    generated_code = Column(Text, nullable=True)
    
    status = Column(String(50), default="created")
    is_running = Column(Boolean, default=False)
    created_at = Column(DateTime, default=func.now())
    pid = Column(Integer, nullable=True)

    owner = relationship("User", back_populates="bots") 