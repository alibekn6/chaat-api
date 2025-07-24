import os
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base


Base = declarative_base()

load_dotenv()

ASYNC_DATABASE_URL = os.getenv("SQLALCHEMY_DATABASE_URL")
if not ASYNC_DATABASE_URL:
    raise RuntimeError("SQLALCHEMY_DATABASE_URL must be set in environment variables.")


AsyncSessionLocal = sessionmaker(
    class_=AsyncSession,
    expire_on_commit=False,
)

async def get_async_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session


SYNC_DATABASE_URL = os.getenv("DATABASE_URL")
if not SYNC_DATABASE_URL:
    raise RuntimeError("DATABASE_URL must be set in environment variables.")
