"""
Модели для системы воркеров и referral'ов

Иерархия:
- Admin выдает права Worker'ам
- Worker создает CheckCode's (чеки) с подарками/звездами
- User активирует CheckCode и привязывается к Worker'у
- User становится referral для Worker'а
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, ForeignKey, Text, Enum
import enum

from app.database import Base


class WorkerRole(str, enum.Enum):
    """Роли воркеров"""
    WORKER = "worker"      # Обычный воркер
    ADMIN = "admin"        # Админ с полным доступом


class Worker(Base):
    """Модель воркера (партнера)"""
    __tablename__ = "workers"

    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(String, unique=True, index=True)
    user_id = Column(String)  # Для связи с User моделью
    
    # Информация о воркере
    name = Column(String, nullable=False)
    email = Column(String, nullable=True)
    
    # Роль и права
    role = Column(Enum(WorkerRole), default=WorkerRole.WORKER)
    is_active = Column(Boolean, default=True)
    
    # Лимиты
    daily_limit = Column(Float)  # Звезд в день
    total_limit = Column(Float, nullable=True)  # Всего звезд
    remaining_daily = Column(Float)  # Осталось на сегодня
    
    # Статистика
    referrals_count = Column(Integer, default=0)  # Привязанных пользователей
    codes_created = Column(Integer, default=0)  # Всего чеков создано
    codes_activated = Column(Integer, default=0)  # Активировано чеков
    total_distributed = Column(Float, default=0.0)  # Всего распределено звезд
    
    # История
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    approved_by = Column(String, nullable=True)  # ID админа, выдавшего права
    approved_at = Column(DateTime, nullable=True)
    
    # Контакты для уведомлений
    notification_chat_id = Column(String, nullable=True)  # Telegram chat для уведомлений


class CheckCode(Base):
    """Модель чека (кода для активации подарка)"""
    __tablename__ = "check_codes"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String, unique=True, index=True)  # Уникальный код (ABC-123-XYZ)
    
    # Владелец чека
    worker_id = Column(Integer, ForeignKey("workers.id"), index=True)
    
    # Содержимое чека
    gift_id = Column(String, nullable=True)  # ID подарка (если NULL - это звезды)
    gift_quantity = Column(Integer, default=1)  # Количество подарков
    stars_amount = Column(Float, default=0.0)  # Количество звезд
    
    # Опциональный текст
    description = Column(Text, nullable=True)  # "Спецпредложение для ВИП"
    
    # Статус
    is_active = Column(Boolean, default=True)
    is_used = Column(Boolean, default=False)
    
    # История активации
    used_by = Column(String, nullable=True)  # Telegram ID того, кто активировал
    used_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)  # Если NULL - не истекает
    
    # Аналитика
    clicks = Column(Integer, default=0)  # Сколько раз кликали по ссылке
    shared_count = Column(Integer, default=0)  # Сколько раз поделились
    
    # Даты
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class UserWorkerBinding(Base):
    """Модель привязки пользователя к воркеру (referral)"""
    __tablename__ = "user_worker_bindings"

    id = Column(Integer, primary_key=True, index=True)
    
    # Пользователь и воркер
    user_telegram_id = Column(String, index=True)  # Привязанный пользователь
    worker_id = Column(Integer, ForeignKey("workers.id"), index=True)
    
    # История привязки
    code_used = Column(String, nullable=True)  # Какой код использовал
    bound_at = Column(DateTime, default=datetime.utcnow)
    
    # Статус
    is_active = Column(Boolean, default=True)
    
    # Уникальность: один пользователь -> один воркер
    # (Последняя привязка перезаписывает предыдущую)
    
    def __repr__(self):
        return f"<UserWorkerBinding user={self.user_telegram_id} -> worker={self.worker_id}>"


class WorkerNotification(Base):
    """Модель уведомлений для воркеров"""
    __tablename__ = "worker_notifications"

    id = Column(Integer, primary_key=True, index=True)
    
    # Получатель
    worker_id = Column(Integer, ForeignKey("workers.id"), index=True)
    is_for_admin = Column(Boolean, default=False)  # Отправить админу?
    
    # Содержание
    type = Column(String)  # "code_activated", "gift_sent", "stars_withdrawn" и т.д.
    title = Column(String)
    message = Column(Text)
    data = Column(String, nullable=True)  # JSON с доп. информацией
    
    # Статус
    is_read = Column(Boolean, default=False)
    read_at = Column(DateTime, nullable=True)
    
    # Даты
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<WorkerNotification {self.type} for worker={self.worker_id}>"


class WorkerActivityLog(Base):
    """Расширенный лог активности для воркеров и админов"""
    __tablename__ = "worker_activity_logs"

    id = Column(Integer, primary_key=True, index=True)
    
    # Кто и что
    worker_id = Column(Integer, ForeignKey("workers.id"), nullable=True)
    affected_user = Column(String, nullable=True)  # Telegram ID затронутого пользователя
    admin_id = Column(String, nullable=True)  # Если админ что-то сделал
    
    # Действие
    action = Column(String)  # "create_code", "activate_code", "transfer_gift" и т.д.
    description = Column(Text)
    
    # Результат
    status = Column(String)  # "success", "error", "warning"
    details = Column(String, nullable=True)  # JSON с деталями
    
    # Видимость логов
    visible_to_worker = Column(Boolean, default=True)  # Видно ли воркеру?
    visible_to_admin = Column(Boolean, default=True)  # Видно ли админу?
    
    # Дата
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<WorkerActivityLog {self.action} - {self.status}>"
