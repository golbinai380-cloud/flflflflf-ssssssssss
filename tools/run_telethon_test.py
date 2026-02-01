"""Короткий тестовый скрипт для вызова telethon_service.create_session
Запускается локально в окружении проекта. Возвращает и печатает результат.
"""
import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv

# Загружаем .env из backend
env_path = Path(__file__).parents[1] / 'backend' / '.env'
if env_path.exists():
    load_dotenv(env_path)

from app.services.telethon_service import telethon_service
from app.database import AsyncSessionLocal

SERVICE_PHONE = os.getenv('SERVICE_ACCOUNT_PHONE')

async def main():
    if not SERVICE_PHONE:
        print('SERVICE_ACCOUNT_PHONE not set in backend/.env')
        return

    async with AsyncSessionLocal() as db:
        res = await telethon_service.create_session(phone_number=SERVICE_PHONE, user_telegram_id='test_run', db=db)
        print('RESULT:', res)

if __name__ == '__main__':
    asyncio.run(main())
