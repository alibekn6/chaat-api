#!/usr/bin/env python3
"""
Диагностический скрипт для проверки AI системы
Запускать на сервере для поиска проблем
"""

import os
import sys
import asyncio
from pathlib import Path
from datetime import datetime
import traceback

async def check_environment():
    """Проверяет переменные окружения"""
    print("=== 🌍 ПРОВЕРКА ПЕРЕМЕННЫХ ОКРУЖЕНИЯ ===")
    
    required_vars = {
        "OPENAI_API_KEY": "OpenAI API для embeddings и chat completion",
        "DATABASE_URL": "Подключение к PostgreSQL",
    }
    
    optional_vars = {
        "BOT_TOKEN": "Telegram bot token (для тестирования)",
        "CHROMA_DB_PATH": "Путь к ChromaDB (по умолчанию: db/chroma_db)",
    }
    
    issues = []
    
    for var, description in required_vars.items():
        value = os.getenv(var)
        if not value:
            print(f"❌ {var}: НЕ УСТАНОВЛЕНА - {description}")
            issues.append(f"Missing {var}")
        else:
            # Маскируем секретные ключи
            if "KEY" in var or "TOKEN" in var:
                masked = value[:8] + "..." + value[-4:] if len(value) > 12 else "***"
                print(f"✅ {var}: {masked}")
            else:
                print(f"✅ {var}: {value}")
    
    for var, description in optional_vars.items():
        value = os.getenv(var)
        if value:
            if "KEY" in var or "TOKEN" in var:
                masked = value[:8] + "..." + value[-4:] if len(value) > 12 else "***"
                print(f"✅ {var}: {masked}")
            else:
                print(f"✅ {var}: {value}")
        else:
            print(f"⚠️  {var}: не установлена (опционально) - {description}")
    
    return issues


async def check_directories():
    """Проверяет необходимые директории"""
    print("\n=== 📁 ПРОВЕРКА ДИРЕКТОРИЙ ===")
    
    directories = {
        "db/chroma_db": "ChromaDB векторная база данных",
        "temp_knowledge_bases": "Временное хранение PDF файлов",
        "temp_bots": "Сгенерированные боты",
        "src/ai/templates": "Шаблоны ботов",
    }
    
    issues = []
    
    for dir_path, description in directories.items():
        path = Path(dir_path)
        
        if not path.exists():
            print(f"❌ {dir_path}: НЕ СУЩЕСТВУЕТ - {description}")
            try:
                path.mkdir(parents=True, exist_ok=True)
                print(f"✅ {dir_path}: СОЗДАНА")
            except Exception as e:
                print(f"❌ {dir_path}: ОШИБКА СОЗДАНИЯ - {e}")
                issues.append(f"Cannot create {dir_path}")
        else:
            # Проверяем права доступа
            if path.is_dir():
                try:
                    # Тестируем запись
                    test_file = path / f"test_write_{datetime.now().timestamp()}"
                    test_file.touch()
                    test_file.unlink()
                    print(f"✅ {dir_path}: ДОСТУПНА (чтение/запись)")
                except Exception as e:
                    print(f"❌ {dir_path}: НЕТ ПРАВ ЗАПИСИ - {e}")
                    issues.append(f"No write permission for {dir_path}")
            else:
                print(f"❌ {dir_path}: НЕ ДИРЕКТОРИЯ")
                issues.append(f"{dir_path} is not a directory")
    
    return issues


async def check_openai_connection():
    """Проверяет подключение к OpenAI API"""
    print("\n=== 🤖 ПРОВЕРКА OPENAI API ===")
    
    try:
        import openai
        
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            print("❌ OpenAI API key не найден")
            return ["OpenAI API key missing"]
        
        client = openai.AsyncOpenAI(api_key=api_key)
        
        # Тестируем простой запрос
        print("🔄 Тестирую OpenAI API...")
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": "Hello, test message"}],
            max_tokens=10
        )
        
        print("✅ OpenAI Chat API: РАБОТАЕТ")
        
        # Тестируем embeddings
        print("🔄 Тестирую OpenAI Embeddings...")
        embeddings_response = await client.embeddings.create(
            model="text-embedding-3-small",
            input=["test text for embeddings"]
        )
        
        print("✅ OpenAI Embeddings API: РАБОТАЕТ")
        print(f"   Размерность embedding: {len(embeddings_response.data[0].embedding)}")
        
        return []
        
    except Exception as e:
        print(f"❌ OpenAI API: ОШИБКА - {e}")
        print(f"   Traceback: {traceback.format_exc()}")
        return [f"OpenAI API error: {str(e)}"]


async def check_chromadb():
    """Проверяет ChromaDB"""
    print("\n=== 🔍 ПРОВЕРКА CHROMADB ===")
    
    try:
        import chromadb
        
        # Используем тот же путь что и в коде
        chroma_path = "db/chroma_db"
        print(f"🔄 Подключаюсь к ChromaDB: {chroma_path}")
        
        client = chromadb.PersistentClient(path=chroma_path)
        
        # Проверяем существующие коллекции
        collections = client.list_collections()
        print(f"✅ ChromaDB подключена: {len(collections)} коллекций")
        
        for collection in collections:
            print(f"   📚 Коллекция: {collection.name}")
            count = collection.count()
            print(f"      Документов: {count}")
        
        # Тестируем создание тестовой коллекции
        test_collection_name = f"test_collection_{datetime.now().timestamp()}"
        try:
            test_collection = client.create_collection(name=test_collection_name)
            test_collection.add(
                embeddings=[[1.0, 2.0, 3.0]],
                documents=["test document"],
                ids=["test_id"]
            )
            
            # Тестируем запрос
            results = test_collection.query(
                query_embeddings=[[1.0, 2.0, 3.0]],
                n_results=1
            )
            
            # Удаляем тестовую коллекцию
            client.delete_collection(name=test_collection_name)
            
            print("✅ ChromaDB операции: РАБОТАЮТ")
            
        except Exception as e:
            print(f"❌ ChromaDB тестирование: ОШИБКА - {e}")
            return [f"ChromaDB test failed: {str(e)}"]
        
        return []
        
    except Exception as e:
        print(f"❌ ChromaDB: ОШИБКА - {e}")
        print(f"   Traceback: {traceback.format_exc()}")
        return [f"ChromaDB error: {str(e)}"]


async def check_database():
    """Проверяет подключение к базе данных"""
    print("\n=== 🗄️ ПРОВЕРКА БАЗЫ ДАННЫХ ===")
    
    try:
        from src.database import get_async_db
        from src.bots.crud import get_bot
        from sqlalchemy import text
        
        async for db in get_async_db():
            # Простая проверка подключения
            result = await db.execute(text("SELECT 1"))
            print("✅ База данных: ПОДКЛЮЧЕНА")
            
            # Проверяем таблицы
            tables_result = await db.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                AND table_name IN ('bots', 'users')
            """))
            
            tables = [row[0] for row in tables_result.fetchall()]
            print(f"✅ Таблицы найдены: {tables}")
            
            # Проверяем новые колонки в bots
            columns_result = await db.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'bots'
                AND column_name IN ('bot_type', 'knowledge_base_status')
            """))
            
            columns = [row[0] for row in columns_result.fetchall()]
            if 'bot_type' in columns and 'knowledge_base_status' in columns:
                print("✅ Новые колонки: bot_type, knowledge_base_status найдены")
            else:
                print(f"⚠️  Новые колонки: найдены только {columns}")
                print("   Возможно нужно запустить миграцию: alembic upgrade head")
            
            break
        
        return []
        
    except Exception as e:
        print(f"❌ База данных: ОШИБКА - {e}")
        print(f"   Traceback: {traceback.format_exc()}")
        return [f"Database error: {str(e)}"]


async def check_pdf_processing():
    """Проверяет PDF обработку"""
    print("\n=== 📄 ПРОВЕРКА PDF ОБРАБОТКИ ===")
    
    try:
        import PyPDF2
        from langchain_text_splitters import RecursiveCharacterTextSplitter
        
        print("✅ PyPDF2: ИМПОРТ OK")
        print("✅ langchain_text_splitters: ИМПОРТ OK")
        
        # Тестируем text splitter
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=100,
            length_function=len,
        )
        
        test_text = "This is a test document. " * 100  # Создаем текст для разбиения
        chunks = splitter.split_text(test_text)
        
        print(f"✅ Text splitting: {len(chunks)} chunks создано")
        
        return []
        
    except Exception as e:
        print(f"❌ PDF обработка: ОШИБКА - {e}")
        print(f"   Traceback: {traceback.format_exc()}")
        return [f"PDF processing error: {str(e)}"]


async def check_templates():
    """Проверяет шаблоны ботов"""
    print("\n=== 📋 ПРОВЕРКА ШАБЛОНОВ ===")
    
    try:
        from src.ai.generator import load_template
        
        templates = [
            "qa_bot_template.py",
            "simple_chat_template.py"
        ]
        
        issues = []
        
        for template_name in templates:
            try:
                template_content = load_template(template_name)
                if "{{BOT_ID}}" in template_content:
                    print(f"✅ {template_name}: НАЙДЕН и содержит плейсхолдеры")
                else:
                    print(f"⚠️  {template_name}: найден но НЕТ плейсхолдеров")
                    issues.append(f"Template {template_name} missing placeholders")
            except Exception as e:
                print(f"❌ {template_name}: ОШИБКА - {e}")
                issues.append(f"Template {template_name} error: {str(e)}")
        
        return issues
        
    except Exception as e:
        print(f"❌ Система шаблонов: ОШИБКА - {e}")
        return [f"Template system error: {str(e)}"]


async def run_comprehensive_test():
    """Запускает комплексный тест системы"""
    print("\n=== 🧪 КОМПЛЕКСНЫЙ ТЕСТ ===")
    
    try:
        # Тестируем полный цикл создания знаний
        from src.ai.knowledge import chroma_client
        from src.ai.generator import _get_knowledge_base_preview
        
        # Создаем тестовую коллекцию
        test_bot_id = 99999
        collection_name = f"bot_{test_bot_id}_kb"
        
        # Удаляем если существует
        try:
            chroma_client.delete_collection(name=collection_name)
        except:
            pass
        
        # Создаем коллекцию
        collection = chroma_client.create_collection(
            name=collection_name,
            metadata={"bot_id": test_bot_id}
        )
        
        # Добавляем тестовые данные
        import openai
        client = openai.AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        test_docs = [
            "Our company provides excellent customer service.",
            "We offer 24/7 support to all our customers.",
            "Our products are high quality and affordable."
        ]
        
        # Генерируем embeddings
        embeddings_response = await client.embeddings.create(
            model="text-embedding-3-small",
            input=test_docs
        )
        
        embeddings = [emb.embedding for emb in embeddings_response.data]
        
        # Добавляем в коллекцию
        collection.add(
            embeddings=embeddings,
            documents=test_docs,
            ids=[f"test_doc_{i}" for i in range(len(test_docs))]
        )
        
        print("✅ Тестовая коллекция создана")
        
        # Тестируем поиск
        query_response = await client.embeddings.create(
            model="text-embedding-3-small",
            input=["customer service"]
        )
        
        results = collection.query(
            query_embeddings=[query_response.data[0].embedding],
            n_results=2
        )
        
        print(f"✅ Поиск работает: найдено {len(results['documents'][0])} документов")
        
        # Тестируем preview
        try:
            preview = await _get_knowledge_base_preview(test_bot_id)
            print(f"✅ Генерация preview: {len(preview)} символов")
        except Exception as e:
            print(f"⚠️  Preview генерация: ОШИБКА - {e}")
        
        # Удаляем тестовую коллекцию
        chroma_client.delete_collection(name=collection_name)
        print("✅ Комплексный тест завершен успешно")
        
        return []
        
    except Exception as e:
        print(f"❌ Комплексный тест: ОШИБКА - {e}")
        print(f"   Traceback: {traceback.format_exc()}")
        return [f"Comprehensive test failed: {str(e)}"]


async def main():
    """Главная функция диагностики"""
    print("🔍 ДИАГНОСТИКА AI СИСТЕМЫ")
    print("=" * 50)
    
    all_issues = []
    
    # Запускаем все проверки
    issues = await check_environment()
    all_issues.extend(issues)
    
    issues = await check_directories()
    all_issues.extend(issues)
    
    issues = await check_database()
    all_issues.extend(issues)
    
    issues = await check_openai_connection()
    all_issues.extend(issues)
    
    issues = await check_chromadb()
    all_issues.extend(issues)
    
    issues = await check_pdf_processing()
    all_issues.extend(issues)
    
    issues = await check_templates()
    all_issues.extend(issues)
    
    # Если основные проверки прошли, запускаем комплексный тест
    if not all_issues:
        issues = await run_comprehensive_test()
        all_issues.extend(issues)
    
    # Итоговый отчет
    print("\n" + "=" * 50)
    print("📊 ИТОГОВЫЙ ОТЧЕТ")
    
    if not all_issues:
        print("🎉 ВСЕ ПРОВЕРКИ ПРОШЛИ УСПЕШНО!")
        print("   AI система должна работать корректно.")
    else:
        print(f"❌ НАЙДЕНО {len(all_issues)} ПРОБЛЕМ:")
        for i, issue in enumerate(all_issues, 1):
            print(f"   {i}. {issue}")
        
        print("\n🔧 РЕКОМЕНДАЦИИ:")
        if any("OpenAI" in issue for issue in all_issues):
            print("   - Проверьте OPENAI_API_KEY в переменных окружения")
            print("   - Убедитесь что у API key есть доступ к gpt-4o-mini и text-embedding-3-small")
        
        if any("ChromaDB" in issue for issue in all_issues):
            print("   - Проверьте права доступа к директории db/chroma_db/")
            print("   - Убедитесь что диск не заполнен")
        
        if any("Database" in issue for issue in all_issues):
            print("   - Проверьте подключение к PostgreSQL")
            print("   - Запустите миграцию: alembic upgrade head")
        
        if any("permission" in issue.lower() for issue in all_issues):
            print("   - Исправьте права доступа: chown -R appuser:appuser /app/")


if __name__ == "__main__":
    asyncio.run(main()) 