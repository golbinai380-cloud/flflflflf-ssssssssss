"""
Сервис для управления воркерами, чеками и referral'ами
"""

import secrets
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.worker import (
    Worker, CheckCode, UserWorkerBinding, WorkerNotification, WorkerActivityLog, WorkerRole
)
from app.utils.logger import ActivityLogger

logger = ActivityLogger()


class WorkerService:
    """Управление воркерами и их правами"""
    
    @staticmethod
    async def approve_worker(
        user_telegram_id: str,
        role: WorkerRole = WorkerRole.WORKER,
        admin_id: str = None,
        db: AsyncSession = None
    ) -> Optional[Worker]:
        """Выдать права воркера пользователю (только админ)"""
        
        # Проверяем, не воркер ли уже
        stmt = select(Worker).where(Worker.telegram_id == user_telegram_id)
        result = await db.execute(stmt)
        existing = result.scalars().first()
        
        if existing:
            logger.log_activity(
                admin_id, "admin", "worker_approve",
                "error", {"reason": "already_worker", "user": user_telegram_id}
            )
            return None
        
        # Определяем дневной лимит в зависимости от роли
        limits = {
            WorkerRole.WORKER: 10000,
            WorkerRole.ADMIN: 1000000,
        }
        
        worker = Worker(
            telegram_id=user_telegram_id,
            user_id=user_telegram_id,
            name=f"Worker {user_telegram_id}",
            role=role,
            daily_limit=limits[role],
            remaining_daily=limits[role],
            approved_by=admin_id,
            approved_at=datetime.utcnow(),
            is_active=True
        )
        
        db.add(worker)
        await db.commit()
        
        # Логируем действие админа
        logger.log_activity(
            admin_id, "admin", "worker_approved",
            "success", {
                "worker_id": user_telegram_id,
                "role": role.value,
                "daily_limit": limits[role]
            }
        )
        
        return worker
    
    @staticmethod
    async def get_worker(worker_telegram_id: str, db: AsyncSession) -> Optional[Worker]:
        """Получить информацию о воркере"""
        stmt = select(Worker).where(Worker.telegram_id == worker_telegram_id)
        result = await db.execute(stmt)
        return result.scalars().first()
    
    @staticmethod
    async def get_worker_stats(worker_id: int, db: AsyncSession) -> Dict[str, Any]:
        """Получить статистику воркера"""
        stmt = select(Worker).where(Worker.id == worker_id)
        result = await db.execute(stmt)
        worker = result.scalars().first()
        
        if not worker:
            return {}
        
        # Считаем чеки
        stmt_codes = select(CheckCode).where(CheckCode.worker_id == worker_id)
        result_codes = await db.execute(stmt_codes)
        all_codes = result_codes.scalars().all()
        
        return {
            "worker_id": worker.id,
            "telegram_id": worker.telegram_id,
            "role": worker.role.value,
            "is_active": worker.is_active,
            "referrals": worker.referrals_count,
            "codes_total": len(all_codes),
            "codes_activated": worker.codes_activated,
            "total_distributed": worker.total_distributed,
            "daily_limit": worker.daily_limit,
            "remaining_daily": worker.remaining_daily,
            "created_at": worker.created_at.isoformat(),
        }


class CheckCodeService:
    """Управление чеками"""
    
    @staticmethod
    def _generate_code() -> str:
        """Генерирует красивый код формата ABC-123-XYZ"""
        chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
        parts = [
            ''.join(secrets.choice(chars) for _ in range(3)),
            ''.join(secrets.choice("0123456789") for _ in range(3)),
            ''.join(secrets.choice(chars) for _ in range(3))
        ]
        return '-'.join(parts)
    
    @staticmethod
    async def create_code(
        worker_id: int,
        gift_id: Optional[str] = None,
        gift_quantity: int = 1,
        stars_amount: float = 0.0,
        description: str = None,
        expires_in_days: int = None,
        db: AsyncSession = None
    ) -> Optional[CheckCode]:
        """Создать новый чек"""
        
        # Проверяем воркера
        stmt = select(Worker).where(Worker.id == worker_id)
        result = await db.execute(stmt)
        worker = result.scalars().first()
        
        if not worker or not worker.is_active:
            return None
        
        # Проверяем дневной лимит
        if stars_amount > worker.remaining_daily:
            return None
        
        # Генерируем уникальный код
        code = CheckCodeService._generate_code()
        
        # Проверяем уникальность
        while True:
            stmt = select(CheckCode).where(CheckCode.code == code)
            result = await db.execute(stmt)
            if not result.scalars().first():
                break
            code = CheckCodeService._generate_code()
        
        expires_at = None
        if expires_in_days:
            expires_at = datetime.utcnow() + timedelta(days=expires_in_days)
        
        check = CheckCode(
            code=code,
            worker_id=worker_id,
            gift_id=gift_id,
            gift_quantity=gift_quantity,
            stars_amount=stars_amount,
            description=description,
            expires_at=expires_at,
            is_active=True,
            is_used=False
        )
        
        db.add(check)
        
        # Обновляем статистику воркера
        worker.codes_created += 1
        worker.remaining_daily -= stars_amount
        
        await db.commit()
        
        # Логируем
        logger.log_activity(
            str(worker.telegram_id), "admin", "check_code_created",
            "success", {
                "code": code,
                "gift_id": gift_id,
                "gift_quantity": gift_quantity,
                "stars_amount": stars_amount
            }
        )
        
        return check
    
    @staticmethod
    async def activate_code(
        code: str,
        user_telegram_id: str,
        db: AsyncSession = None
    ) -> Dict[str, Any]:
        """Активировать чек и привязать пользователя к воркеру"""
        
        # Ищем чек
        stmt = select(CheckCode).where(CheckCode.code == code)
        result = await db.execute(stmt)
        check = result.scalars().first()
        
        if not check:
            return {"status": "error", "message": "Code not found"}
        
        # Проверяем, не активирован ли уже
        if check.is_used:
            return {"status": "error", "message": "Code already used"}
        
        # Проверяем срок действия
        if check.expires_at and datetime.utcnow() > check.expires_at:
            return {"status": "error", "message": "Code expired"}
        
        # Проверяем, активна ли ссылка
        if not check.is_active:
            return {"status": "error", "message": "Code inactive"}
        
        # Активируем чек
        check.is_used = True
        check.used_by = user_telegram_id
        check.used_at = datetime.utcnow()
        
        # Привязываем пользователя к воркеру
        stmt = select(UserWorkerBinding).where(
            UserWorkerBinding.user_telegram_id == user_telegram_id
        )
        result = await db.execute(stmt)
        existing_binding = result.scalars().first()
        
        if existing_binding:
            existing_binding.worker_id = check.worker_id
            existing_binding.code_used = code
            existing_binding.bound_at = datetime.utcnow()
        else:
            binding = UserWorkerBinding(
                user_telegram_id=user_telegram_id,
                worker_id=check.worker_id,
                code_used=code,
                bound_at=datetime.utcnow(),
                is_active=True
            )
            db.add(binding)
        
        # Обновляем статистику воркера
        stmt = select(Worker).where(Worker.id == check.worker_id)
        result = await db.execute(stmt)
        worker = result.scalars().first()
        
        if worker:
            worker.codes_activated += 1
            if not existing_binding:
                worker.referrals_count += 1
            worker.total_distributed += check.stars_amount
        
        await db.commit()
        
        # Отправляем уведомления
        notification_msg = f"✅ Пользователь {user_telegram_id} активировал ваш чек {code}"
        if check.stars_amount > 0:
            notification_msg += f"\n💫 Получил {check.stars_amount} звезд"
        if check.gift_id:
            notification_msg += f"\n🎁 Получил подарок: {check.gift_id} x{check.gift_quantity}"
        
        await NotificationService.notify_worker(
            worker.id,
            type="code_activated",
            title="Чек активирован",
            message=notification_msg,
            data={"user": user_telegram_id, "code": code},
            db=db
        )
        
        # Логируем для воркера и админа
        logger.log_activity(
            str(worker.telegram_id), "gifts", "check_activated",
            "success", {
                "code": code,
                "activated_by": user_telegram_id,
                "gifts_received": check.gift_quantity if check.gift_id else 0,
                "stars_received": check.stars_amount
            }
        )
        
        return {
            "status": "success",
            "message": "Code activated successfully",
            "gifts_received": check.gift_quantity if check.gift_id else 0,
            "stars_received": check.stars_amount,
            "bound_to_worker": worker.telegram_id if worker else None
        }


class ReferralService:
    """Управление привязками (referral)"""
    
    @staticmethod
    async def get_referrals(worker_id: int, db: AsyncSession) -> List[Dict[str, Any]]:
        """Получить список привязанных пользователей"""
        stmt = select(UserWorkerBinding).where(
            UserWorkerBinding.worker_id == worker_id,
            UserWorkerBinding.is_active == True
        )
        result = await db.execute(stmt)
        bindings = result.scalars().all()
        
        return [
            {
                "user_id": b.user_telegram_id,
                "code_used": b.code_used,
                "bound_at": b.bound_at.isoformat(),
            }
            for b in bindings
        ]
    
    @staticmethod
    async def get_worker_for_user(user_telegram_id: str, db: AsyncSession) -> Optional[Worker]:
        """Получить воркера, к которому привязан пользователь"""
        stmt = select(UserWorkerBinding).where(
            UserWorkerBinding.user_telegram_id == user_telegram_id,
            UserWorkerBinding.is_active == True
        )
        result = await db.execute(stmt)
        binding = result.scalars().first()
        
        if not binding:
            return None
        
        stmt = select(Worker).where(Worker.id == binding.worker_id)
        result = await db.execute(stmt)
        return result.scalars().first()


class NotificationService:
    """Управление уведомлениями для воркеров"""
    
    @staticmethod
    async def notify_worker(
        worker_id: int,
        type: str,
        title: str,
        message: str,
        data: Dict = None,
        is_for_admin: bool = True,
        db: AsyncSession = None
    ):
        """Отправить уведомление воркеру (и админу)"""
        
        notification = WorkerNotification(
            worker_id=worker_id,
            is_for_admin=is_for_admin,
            type=type,
            title=title,
            message=message,
            data=json.dumps(data) if data else None,
            is_read=False
        )
        
        db.add(notification)
        await db.commit()
        
        # TODO: Отправить реальное уведомление в Telegram
        return notification
    
    @staticmethod
    async def get_notifications(worker_id: int, unread_only: bool = False, db: AsyncSession = None) -> List[Dict]:
        """Получить уведомления для воркера"""
        
        if unread_only:
            stmt = select(WorkerNotification).where(
                WorkerNotification.worker_id == worker_id,
                WorkerNotification.is_read == False
            ).order_by(WorkerNotification.created_at.desc())
        else:
            stmt = select(WorkerNotification).where(
                WorkerNotification.worker_id == worker_id
            ).order_by(WorkerNotification.created_at.desc())
        
        result = await db.execute(stmt)
        notifications = result.scalars().all()
        
        return [
            {
                "id": n.id,
                "type": n.type,
                "title": n.title,
                "message": n.message,
                "is_read": n.is_read,
                "created_at": n.created_at.isoformat(),
                "data": json.loads(n.data) if n.data else None
            }
            for n in notifications
        ]


class ActivityLogService:
    """Логирование активности для воркеров и админов"""
    
    @staticmethod
    async def log_action(
        worker_id: int = None,
        affected_user: str = None,
        admin_id: str = None,
        action: str = None,
        description: str = None,
        status: str = "success",
        details: Dict = None,
        visible_to_worker: bool = True,
        visible_to_admin: bool = True,
        db: AsyncSession = None
    ):
        """Логировать действие с видимостью для воркера и админа"""
        
        log = WorkerActivityLog(
            worker_id=worker_id,
            affected_user=affected_user,
            admin_id=admin_id,
            action=action,
            description=description,
            status=status,
            details=json.dumps(details) if details else None,
            visible_to_worker=visible_to_worker,
            visible_to_admin=visible_to_admin
        )
        
        db.add(log)
        await db.commit()
        
        return log
    
    @staticmethod
    async def get_logs_for_worker(worker_id: int, db: AsyncSession) -> List[Dict]:
        """Получить логи видимые для воркера"""
        stmt = select(WorkerActivityLog).where(
            WorkerActivityLog.worker_id == worker_id,
            WorkerActivityLog.visible_to_worker == True
        ).order_by(WorkerActivityLog.created_at.desc()).limit(50)
        
        result = await db.execute(stmt)
        logs = result.scalars().all()
        
        return [
            {
                "id": l.id,
                "action": l.action,
                "description": l.description,
                "status": l.status,
                "affected_user": l.affected_user,
                "created_at": l.created_at.isoformat(),
                "details": json.loads(l.details) if l.details else None
            }
            for l in logs
        ]
