import os
from sqlalchemy import create_engine
from sqlalchemy.schema import CreateTable

# Важно: импортируй тот же самый базовый класс, что и в env.py
from src.database import Base 

# Импортируй все твои модули с моделями, чтобы они зарегистрировались
import src.auth.schema
import src.bots.schema
import src.feedbacks.models
# Добавь сюда другие импорты, если есть еще модели

# Нам не нужна реальная база, мы просто хотим сгенерировать SQL
# Используем фиктивный URL, но с правильным диалектом
db_url = "postgresql://user:pass@host/db"
engine = create_engine(db_url)

print("--- SQL DDL STATEMENTS ---")
# Проходим по всем таблицам, которые "знает" наш Base
for table in Base.metadata.sorted_tables:
    # Генерируем команду CREATE TABLE для каждой таблицы
    print(str(CreateTable(table).compile(engine)).strip() + ";")
print("--- END OF SQL ---")
