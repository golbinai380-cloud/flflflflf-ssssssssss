#!/usr/bin/env python3
"""
Единый файл запуска всего бэкенда
Запускает API и Бота в одном процессе
"""

import os
import sys
import asyncio
import logging
from pathlib import Path

# Добавляем текущую директорию в PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent))

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("single_runner")

# Загружаем .env
from dotenv import load_dotenv
env_path = Path(__file__).parent / ".env"
if not env_path.exists():
    logger.error(f"❌ Файл .env не найден: {env_path}")
    sys.exit(1)

load_dotenv(env_path)
logger.info(f"✅ .env файл загружен из {env_path}")

# Проверяем критические переменные
REQUIRED_ENV = ["TELEGRAM_BOT_TOKEN", "ADMIN_ID"]
missing = [var for var in REQUIRED_ENV if not os.getenv(var)]
if missing:
    logger.error(f"❌ Отсутствуют переменные: {', '.join(missing)}")
    sys.exit(1)

logger.info("✅ Все переменные окружения загружены")


async def run_api():
    """Запускает FastAPI сервер"""
    import uvicorn
    
    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", 8000))
    
    logger.info(f"🚀 Запуск API на {host}:{port}")
    
    config = uvicorn.Config(
        "app.main:app",
        host=host,
        port=port,
        log_level="info",
        reload=False  # Отключаем reload для стабильности
    )
    server = uvicorn.Server(config)
    await server.serve()


async def run_bot():
    """Запускает Telegram бота"""
    from app.bot import main as bot_main
    
    logger.info("🤖 Запуск Telegram бота")
    await bot_main()


async def main():
    """Главная функция - запускает API и Бота параллельно"""
    logger.info("=" * 60)
    logger.info("🚀 ЗАПУСК TELEGRAM MINI APP BACKEND")
    logger.info("=" * 60)
    
    # Инициализируем БД
    try:
        from app.database import init_db
        await init_db()
        logger.info("✅ База данных инициализирована")
    except Exception as e:
        logger.error(f"❌ Ошибка инициализации БД: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    logger.info("")
    logger.info("📋 Запущенные сервисы:")
    logger.info(f"   • API: http://{os.getenv('API_HOST', '0.0.0.0')}:{os.getenv('API_PORT', 8000)}")
    logger.info(f"   • Docs: http://{os.getenv('API_HOST', '0.0.0.0')}:{os.getenv('API_PORT', 8000)}/docs")
    logger.info(f"   • Bot: @{os.getenv('BOT_USERNAME', 'unknown')}")
    logger.info("")
    logger.info("✅ Всё готово! Нажмите Ctrl+C для остановки")
    logger.info("=" * 60)
    
    # Запускаем API и Бота параллельно
    try:
        await asyncio.gather(
            run_api(),
            run_bot()
        )
    except KeyboardInterrupt:
        logger.info("\n⏹️  Остановка сервисов...")
    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("👋 До свидания!")
    except Exception as e:
        logger.error(f"❌ Ошибка запуска: {e}")
        sys.exit(1)
