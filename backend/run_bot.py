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
logger = logging.getLogger("bot_runner")

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

# НЕ меняем директорию! Оставляем в корне проекта
# os.chdir(backend_dir)  # УБРАНО

# Запускаем бота
if __name__ == "__main__":
    try:
        # Проверяем токен ПЕРЕД импортом бота
        bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
        if not bot_token:
            logger.error("❌ TELEGRAM_BOT_TOKEN не установлен в .env!")
            logger.error("   Пожалуйста, заполните .env файл с корректным токеном")
            sys.exit(1)
        
        if len(bot_token) < 10:
            logger.error("❌ TELEGRAM_BOT_TOKEN имеет неправильный формат!")
            logger.error("   Токен должен быть примерно 50+ символов")
            sys.exit(1)
        
        logger.info(f"✅ Токен бота загружен (первые 10 символов: {bot_token[:10]})")
        
        # Проверяем админа
        admin_id = os.getenv("ADMIN_ID", "")
        if not admin_id:
            logger.warning("⚠️  ADMIN_ID не установлен - некоторые функции не будут работать")
        else:
            logger.info(f"✅ Admin ID установлен: {admin_id}")
        
        logger.info("🤖 Запуск Telegram бота...")
        logger.info("   Бот слушает сообщения...")
        logger.info("   Отправьте /start боту чтобы начать")
        logger.info("   Нажмите Ctrl+C чтобы остановить")
        
        from app.bot import main
        asyncio.run(main())
        
    except KeyboardInterrupt:
        logger.info("⏹️  Бот остановлен пользователем")
        sys.exit(0)
    except Exception as e:
        logger.error(f"❌ Ошибка при запуске бота: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
