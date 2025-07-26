from fastapi import FastAPI, HTTPException, Depends, Request, status
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import RequestValidationError
from contextlib import asynccontextmanager
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from fastapi.middleware.cors import CORSMiddleware
from src.database import get_async_db, AsyncSessionLocal, ASYNC_DATABASE_URL
from src.database import Base, ASYNC_DATABASE_URL
from src.auth.api import router as auth_router
from src.bots.api import router as bots_router
from src.ai.router import router as ai_router
from src.feedbacks.api import router as feedbacks_router
import logging
from pathlib import Path
from src.utils.azure_config import azure_settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting application...")


    # --- ВРЕМЕННЫЙ КОД ДЛЯ СОЗДАНИЯ ТАБЛИЦ --- это мне помогло когда не создавались таблицы в alembic
    # engine = create_async_engine(ASYNC_DATABASE_URL)
    # async with engine.begin() as conn:
    #     # Эта команда создаст все таблицы, которые "видит" Base
    #     await conn.run_sync(Base.metadata.create_all)
    # await engine.dispose()
    # logger.info("Initial tables created (if they didn't exist).")
    # --- КОНЕЦ ВРЕМЕННОГО КОДА ---


    # --- ИНИЦИАЛИЗАЦИЯ БАЗЫ ДАННЫХ ---
    # Создаем асинхронный движок ТОЛЬКО при старте приложения
    engine = create_async_engine(ASYNC_DATABASE_URL, echo=True, future=True)
    # Привязываем нашу "фабрику" сессий к этому движку
    AsyncSessionLocal.configure(bind=engine)
    logger.info("Database engine created and session configured.")
    # ------------------------------------
    
    # Create local storage directory
    local_storage_dir = Path(azure_settings.local_storage_path)
    local_storage_dir.mkdir(exist_ok=True)
    logger.info(f"Local storage directory: {local_storage_dir}")
    
    # Log Azure status
    if azure_settings.azure_sdk_available:
        if azure_settings.azure_storage_enabled:
            logger.info("Azure Storage: ENABLED")
        else:
            logger.info("Azure Storage: DISABLED (using local storage)")
    else:
        logger.warning("Azure SDK not available - falling back to local storage")
    
    yield
    
    # Shutdown
    # Закрываем пул соединений движка
    if 'engine' in locals():
        await engine.dispose()
    logger.info("Shutting down application...")

app = FastAPI(
    title="Chaat API",
    description="API for no-code Telegram bot creation platform",
    version="1.0.0",
    lifespan=lifespan
)

# ... (весь остальной код твоего main.py остается без изменений) ...
# ... (exception_handler, origins, middleware, routers, health checks) ...

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Custom validation error handler to format errors consistently"""
    formatted_errors = []
    for error in exc.errors():
        # Get the field name from location path
        field = error['loc'][-1] if error['loc'] else 'unknown'
        message = error['msg']
        error_type = error.get('type', '')
        
        # Custom error messages for common validation errors
        if 'email' in str(field).lower() and 'value_error' in error_type:
            message = 'Please enter a valid email address'
        elif error_type == 'missing':
            message = f'{field.replace("_", " ").title()} is required'
        elif 'value_error' in error_type and 'Password must be at least' in message:
            message = 'Password must be at least 8 characters long'
        elif 'value_error' in error_type and 'Full name must be at least' in message:
            message = 'Full name must be at least 2 characters long'
        
        formatted_errors.append({
            "field": field,
            "message": message
        })
    
    return JSONResponse(
        status_code=422,
        content={"detail": formatted_errors}
    )


origins = [
    "http://localhost:5173",      
    "http://165.22.95.110:80",
    "https://reeply.works",
    "http://reeply.works",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files for local image serving
app.mount("/static/feedback_images", StaticFiles(directory=azure_settings.local_storage_path), name="feedback_images")

# Include routers
app.include_router(auth_router, prefix="/auth")
app.include_router(bots_router, prefix="/bots")
app.include_router(ai_router, prefix="/ai")
app.include_router(feedbacks_router)

@app.get("/")
async def root():
    return {"message": "Chaat API is running"}

@app.get("/health")
async def health_check():
    return {
        "status": "healthy", 
        "azure_sdk_available": azure_settings.azure_sdk_available,
        "azure_enabled": azure_settings.azure_storage_enabled,
        "storage_mode": "azure" if azure_settings.azure_storage_enabled else "local"
    }

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

# Старый on_event("shutdown") больше не нужен, так как это делается в lifespan
