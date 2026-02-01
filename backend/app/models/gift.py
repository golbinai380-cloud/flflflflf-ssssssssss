from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, ForeignKey

from app.database import Base


class Gift(Base):
    """Модель подарка"""
    __tablename__ = "gifts"

    id = Column(Integer, primary_key=True, index=True)
    telegram_gift_id = Column(String, unique=True, index=True)
    name = Column(String)
    price = Column(Float)
    rarity = Column(String, default="common")  # common, rare, epic, legendary
    image_url = Column(String, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)


class GiftTransaction(Base):
    """Модель транзакции подарков"""
    __tablename__ = "gift_transactions"

    id = Column(Integer, primary_key=True, index=True)
    from_user_id = Column(String, index=True)
    to_user_id = Column(String, index=True)
    gift_id = Column(Integer, ForeignKey("gifts.id"))
    
    status = Column(String, default="pending")  # pending, completed, failed, auto_converted
    auto_converted_to_stars = Column(Float, default=0.0)
    commission = Column(Float, default=0.0)
    
    notes = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
