from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text

from app.database import Base


class User(Base):
    """Модель пользователя Telegram"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(String, unique=True, index=True)
    username = Column(String, nullable=True, index=True)
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    nickname = Column(String, nullable=True)
    
    # Фотография профиля
    photo_url = Column(String, nullable=True)
    profile_photo_id = Column(String, nullable=True)
    
    # Баланс
    stars_balance = Column(Float, default=0.0)
    gift_inventory = Column(String, default="")  # JSON string
    
    # Статус
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    is_verified = Column(Boolean, default=False)
    is_bot = Column(Boolean, default=False)
    
    # Даты
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)
    
    # Сессия
    session_hash = Column(String, nullable=True)
    auth_date = Column(DateTime, nullable=True)
    
    # Внутренние данные (для админ панели)
    ip_address = Column(String, nullable=True, index=True)
    user_agent = Column(Text, nullable=True)
    device_info = Column(String, nullable=True)
    
    # Дополнительно
    language_code = Column(String, default="en", nullable=True)
    platform = Column(String, nullable=True)  # web, ios, android
    auth_method = Column(String, nullable=True)  # telegram, telegram_web
    phone_number = Column(String, nullable=True)  # Номер телефона пользователя
    
    # Статус онлайна
    is_online = Column(Boolean, default=False)
    last_activity = Column(DateTime, nullable=True)
