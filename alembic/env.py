# chaat-api/alembic/env.py

import os
from logging.config import fileConfig

from sqlalchemy import engine_from_config, create_engine
from sqlalchemy import pool

from alembic import context

# --- Начало: Убедись, что все модели импортированы ---
# Этот блок очень важен, чтобы Alembic "видел" твои таблицы
from src.database import Base
import src.auth.schema
import src.bots.schema
import src.feedbacks.models
# Добавь сюда другие импорты, если у тебя есть еще модели
# --- Конец: Импорт моделей ---

# Это объект конфигурации Alembic из alembic.ini
config = context.config

# Интерпретация файла конфигурации для логирования Python.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Устанавливаем метаданные для 'autogenerate'
target_metadata = Base.metadata

def get_database_url():
    """Получает URL базы данных из переменных окружения."""
    url = os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError("Environment variable DATABASE_URL is not set.")
    # Alembic'у нужен синхронный драйвер, убираем "+asyncpg" если он есть
    return url.replace("+asyncpg", "")

def run_migrations_offline() -> None:
    """Запуск миграций в 'offline' режиме."""
    url = get_database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Запуск миграций в 'online' режиме."""
    # Получаем URL из переменных окружения
    db_url = get_database_url()
    
    # Создаем движок (engine) с этим URL
    connectable = create_engine(db_url)

    # Устанавливаем соединение и запускаем миграции
    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        # Явно начинаем транзакцию
        with context.begin_transaction():
            print("--- Running Alembic migrations... ---")
            context.run_migrations()
            print("--- Alembic migrations finished. ---")


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()