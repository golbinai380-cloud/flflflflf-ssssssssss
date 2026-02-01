from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey

from app.database import Base


class Session(Base):
    """Модель сессии пользователя"""
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), index=True)
    session_token = Column(String, unique=True, index=True)
    
    # Telegram данные
    telegram_user_data = Column(String, nullable=True)  # JSON
    
    # Статус
    is_active = Column(Boolean, default=True)
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    
    # Даты
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime)
    last_activity = Column(DateTime, default=datetime.utcnow)
