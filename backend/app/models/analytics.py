from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text

from app.database import Base


class ActivityLog(Base):
    """Модель логирования активности"""
    __tablename__ = "activity_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True)
    
    category = Column(String, index=True)  # "auth", "gifts", "automation", "manual"
    action = Column(String)
    
    details = Column(Text, nullable=True)  # JSON
    status = Column(String)  # "success", "error", "pending"
    
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
