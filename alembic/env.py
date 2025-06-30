import os
from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# Import the Base and all models
from src.database import Base
import src.auth.schema  # Import to register User model
import src.bots.schema  # Import to register Bot model

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Set the target metadata from our Base
target_metadata = Base.metadata

# Set the database URL from environment variables
def get_url():
    # Try async URL first, then sync URL
    url = os.getenv("SQLALCHEMY_DATABASE_URL") or os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL or SQLALCHEMY_DATABASE_URL must be set")
    
    # Convert to sync URL for Alembic (remove +asyncpg)
    if "+asyncpg" in url:
        url = url.replace("+asyncpg", "")
    return url

# Override the URL in config
try:
    final_url = get_url()
    config.set_main_option("sqlalchemy.url", final_url)
except Exception as e:
    print(f"ERROR setting up database URL: {e}")
    raise

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
