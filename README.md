# FastAPI Project with asyncpg and PostgreSQL

## Getting Started

1. Create a virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Set your database URL (optional, defaults to local Postgres):
   ```bash
   export DATABASE_URL=postgresql://user:password@localhost:5432/dbname
   ```
4. Run the app:
   ```bash
   uvicorn src.main:app --reload
   ```

## Structure

- `src/main.py`: FastAPI entrypoint, lifespan, DB pool
- `src/routers/root_router.py`: Health check endpoint
- `src/types/schemas.py`: Pydantic models

## Health Endpoint

- `GET /health` — returns `{ "message": "healthy" }` if DB is reachable 