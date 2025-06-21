# database.py
import os
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Импортируем базовый класс моделей из src/auth/models.py
from src.auth.schema import Base

load_dotenv()

# Асинхронный URL читаем из SQLALCHEMY_DATABASE_URL
ASYNC_DATABASE_URL = os.getenv("SQLALCHEMY_DATABASE_URL")
if not ASYNC_DATABASE_URL:
    raise RuntimeError("SQLALCHEMY_DATABASE_URL must be set in environment variables.")

# Создаем асинхронный движок и фабрику сессий
async_engine = create_async_engine(
    ASYNC_DATABASE_URL,
    echo=True,
    future=True,
)
AsyncSessionLocal = sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# Синхронный URL читаем из DATABASE_URL
SYNC_DATABASE_URL = os.getenv("DATABASE_URL")
if not SYNC_DATABASE_URL:
    raise RuntimeError("DATABASE_URL must be set in environment variables.")

# Синхронный движок и фабрика
sync_engine = create_engine(
    SYNC_DATABASE_URL,
    echo=True,
    pool_pre_ping=True,
    future=True,
)
SyncSessionLocal = sessionmaker(
    bind=sync_engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)

# Зависимости для FastAPI

def get_sync_db():
    db = SyncSessionLocal()
    try:
        yield db
    finally:
        db.close()

async def get_async_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session


def init_db_sync():
    import src.auth.models  # регистрируем модели
    Base.metadata.create_all(bind=sync_engine)

async def init_db():
    import src.auth.models
    async with async_engine.begin() as conn:
        # создаем все таблицы, объявленные в Base
        await conn.run_sync(Base.metadata.create_all)

