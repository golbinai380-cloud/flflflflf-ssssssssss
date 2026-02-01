#!/usr/bin/env python3
import os
import sys
import asyncio
import logging
from pathlib import Path

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("api_runner")

# Добавляем путь к backend (ДО смены директории!)
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

# Загружаем переменные окружения
from dotenv import load_dotenv
env_file = backend_dir / ".env"

# Проверяем ПЕРЕД загрузкой
if not env_file.exists():
    logger.warning(f"⚠️  .env файл не найден в {env_file}")
    logger.warning("   Проверьте, что файл существует и заполнен")
else:
    logger.info(f"✅ .env файл найден в {env_file}")

# Загружаем с явным путем
env_result = load_dotenv(str(env_file))
if env_result:
    logger.info(f"✅ Переменные окружения загружены успешно")
else:
    logger.warning(f"⚠️  load_dotenv() вернула False, переменные могут быть не загружены")

# НЕ меняем директорию! Uvicorn должен запускаться из корня проекта
# os.chdir(backend_dir)  # УБРАНО

# Запускаем API
if __name__ == "__main__":
    try:
        import uvicorn
        
        host = os.getenv("API_HOST", "0.0.0.0")
        port = int(os.getenv("API_PORT", 8000))
        debug = os.getenv("DEBUG", "True").lower() == "true"
        
        logger.info(f"🚀 Запуск API сервера...")
        logger.info(f"   Host: {host}")
        logger.info(f"   Port: {port}")
        logger.info(f"   Debug: {debug}")
        logger.info(f"   URL: http://{host if host != '0.0.0.0' else 'localhost'}:{port}")
        logger.info(f"   Документация: http://{host if host != '0.0.0.0' else 'localhost'}:{port}/docs")
        
        uvicorn.run(
            "app.main:app",
            host=host,
            port=port,
            reload=debug,
            access_log=True,
            log_level="info"
        )
    except Exception as e:
        logger.error(f"❌ Ошибка при запуске API: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
