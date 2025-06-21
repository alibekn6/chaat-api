from fastapi import FastAPI, Depends, status
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.middleware.cors import CORSMiddleware
import asyncio

from src.database import get_async_db, init_db, async_engine
from src.auth.api import router as auth_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # гарантируем, что модели зарегистрированы до создания таблиц
    import src.auth.schema
    await init_db()
    yield



app = FastAPI(lifespan=lifespan)

# Allow all origins for development
origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"], # Allows all methods
    allow_headers=["*"], # Allows all headers
)


# Подключаем маршруты аутентификации и CRUD
app.include_router(auth_router, prefix="/auth", tags=["auth"])

# Корневой health-check
@app.get("/", tags=["root"])
def read_root() -> dict[str, str]:
    return {"message": "API is up and running"}

# Проверка соединения с БД
@app.get("/health/database", tags=["health"], response_model=dict[str, str])
async def check_database_connection(
    session: AsyncSession = Depends(get_async_db)
) -> dict[str, str]:
    try:
        await session.execute(text("SELECT 1"))
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "unhealthy", "detail": str(e)},
        )
    return {"status": "healthy", "detail": "Database connection successful"}

# Shutdown event
@app.on_event("shutdown")
async def on_shutdown() -> None:
    await async_engine.dispose()
