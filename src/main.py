from fastapi import FastAPI, Depends, status, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from contextlib import asynccontextmanager
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.middleware.cors import CORSMiddleware
from src.database import get_async_db, init_db, async_engine, Base
from src.auth.api import router as auth_router
from src.bots.api import router as bots_router
from src.ai.router import router as ai_router
import src.auth.schema
import src.bots.schema

@asynccontextmanager
async def lifespan(app: FastAPI):

    async with async_engine.begin() as conn:
        # dev only
        # await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(
    lifespan=lifespan,
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)


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


app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(bots_router, prefix="/bots", tags=["bots"])
app.include_router(ai_router)

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
