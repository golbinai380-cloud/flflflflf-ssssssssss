import logging
import asyncio
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand
import os
import sys

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Инициализация бота
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")

if not BOT_TOKEN:
    logger.error("❌ TELEGRAM_BOT_TOKEN не установлен в .env!")
    logger.error("Пожалуйста, заполните TELEGRAM_BOT_TOKEN в backend/.env")
    sys.exit(1)

try:
    bot = Bot(token=BOT_TOKEN)
    logger.info(f"✅ Бот инициализирован с токеном")
except Exception as e:
    logger.error(f"❌ Ошибка инициализации бота: {e}")
    sys.exit(1)

# Создаем Dispatcher и storage ВНУТРИ async функции
# чтобы избежать "no current event loop" ошибки в Python 3.8
dp = None
storage = None

from app.handlers.bot import router


async def init_dispatcher():
    """Инициализирует Dispatcher и Storage"""
    global dp, storage
    if dp is None:
        storage = MemoryStorage()
        dp = Dispatcher(storage=storage)
        dp.include_router(router)
    return dp


async def set_commands():
    """Устанавливает команды бота"""
    try:
        commands = [
            BotCommand(command="start", description="Запустить приложение"),
            BotCommand(command="gifts", description="Мой инвентарь подарков"),
            BotCommand(command="balance", description="Проверить баланс звёзд"),
            BotCommand(command="help", description="Справка"),
        ]
        await bot.set_my_commands(commands)
        logger.info("✅ Команды бота установлены")
    except Exception as e:
        logger.error(f"❌ Ошибка при установке команд: {e}")


async def main():
    """Главная функция бота"""
    try:
        # Инициализируем Dispatcher с event loop
        dispatcher = await init_dispatcher()
        
        await set_commands()
        logger.info("🤖 Telegram Bot запущен и слушает сообщения...")
        logger.info("💬 Отправьте /start боту в Telegram чтобы начать")
        
        # Запускаем long polling
        await dispatcher.start_polling(bot, allowed_updates=dispatcher.resolve_used_update_types())
    except Exception as e:
        logger.error(f"❌ Ошибка при запуске бота: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("⏹️  Бот остановлен пользователем")
    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}")
        sys.exit(1)
