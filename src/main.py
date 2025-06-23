from fastapi import FastAPI, Depends, status
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.middleware.cors import CORSMiddleware
from src.database import get_async_db, init_db, async_engine, Base
from src.auth.api import router as auth_router
from src.bots.api import router as bots_router
import src.auth.schema
import src.bots.schema

@asynccontextmanager
async def lifespan(app: FastAPI):

    async with async_engine.begin() as conn:
        # dev only
        # await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(lifespan=lifespan)

origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"], 
    allow_headers=["*"],
)


app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(bots_router, prefix="/bots", tags=["bots"])


@app.get("/", tags=["root"])
def read_root() -> dict[str, str]:
    return {"message": "API is up and running"}

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

@app.on_event("shutdown")
async def on_shutdown() -> None:
    await async_engine.dispose()
