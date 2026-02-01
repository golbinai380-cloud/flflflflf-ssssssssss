"""
API для Admin Panel
"""
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from datetime import datetime, timedelta
from pydantic import BaseModel
from typing import Optional
import os

from app.database import get_db
from app.services import AuthService
from app.models.user import User
from app.models.worker import Worker, WorkerRole
from app.models.telegram_session import GiftTransfer, IPHistory, Broadcast
from app.utils.logger import ActivityLogger

router = APIRouter(prefix="/api/admin-panel", tags=["admin-panel"])
auth_service = AuthService(os.getenv("TELEGRAM_BOT_TOKEN", ""))
logger = ActivityLogger()
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))


async def get_current_admin(token: str = Query(...), db: AsyncSession = Depends(get_db)):
    """Проверяет, что пользователь является админом"""
    user_id = await auth_service.validate_session(token, db)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    if int(user_id) != ADMIN_ID:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    return user_id


# ============================================================================
# УПРАВЛЕНИЕ ПОЛЬЗОВАТЕЛЯМИ
# ============================================================================

@router.get("/users")
async def get_all_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    search: str = Query(""),
    token: str = Query(...),
    db: AsyncSession = Depends(get_db)
):
    """Получить список всех пользователей"""
    
    await get_current_admin(token, db)
    
    stmt = select(User)
    
    if search:
        search_term = f"%{search}%"
        stmt = stmt.where(
            or_(
                User.username.ilike(search_term),
                User.first_name.ilike(search_term),
                User.telegram_id.ilike(search_term)
            )
        )
    
    stmt = stmt.offset(skip).limit(limit)
    result = await db.execute(stmt)
    users = result.scalars().all()
    
    return JSONResponse({
        "status": "success",
        "users": [
            {
                "telegram_id": u.telegram_id,
                "username": u.username,
                "first_name": u.first_name,
                "last_name": u.last_name,
                "phone_number": u.phone_number,
                "is_active": u.is_active,
                "is_admin": u.is_admin,
                "stars_balance": u.stars_balance,
                "created_at": u.created_at.isoformat() if u.created_at else None,
                "last_activity": u.last_activity.isoformat() if u.last_activity else None
            }
            for u in users
        ]
    })


@router.post("/users/{user_id}/block")
async def block_user(
    user_id: str,
    token: str = Query(...),
    db: AsyncSession = Depends(get_db)
):
    """Заблокировать пользователя"""
    
    await get_current_admin(token, db)
    
    stmt = select(User).where(User.telegram_id == user_id)
    result = await db.execute(stmt)
    user = result.scalars().first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user.is_active = False
    await db.commit()
    
    logger.log_activity(
        str(ADMIN_ID),
        "admin",
        "user_blocked",
        "success",
        {"user_id": user_id}
    )
    
    return JSONResponse({
        "status": "success",
        "message": f"User {user_id} blocked"
    })


@router.post("/users/{user_id}/unblock")
async def unblock_user(
    user_id: str,
    token: str = Query(...),
    db: AsyncSession = Depends(get_db)
):
    """Разблокировать пользователя"""
    
    await get_current_admin(token, db)
    
    stmt = select(User).where(User.telegram_id == user_id)
    result = await db.execute(stmt)
    user = result.scalars().first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user.is_active = True
    await db.commit()
    
    logger.log_activity(
        str(ADMIN_ID),
        "admin",
        "user_unblocked",
        "success",
        {"user_id": user_id}
    )
    
    return JSONResponse({
        "status": "success",
        "message": f"User {user_id} unblocked"
    })


# ============================================================================
# УПРАВЛЕНИЕ ВОРКЕРАМИ
# ============================================================================

@router.get("/workers")
async def get_all_workers(
    token: str = Query(...),
    db: AsyncSession = Depends(get_db)
):
    """Получить список всех воркеров"""
    
    await get_current_admin(token, db)
    
    stmt = select(Worker)
    result = await db.execute(stmt)
    workers = result.scalars().all()
    
    return JSONResponse({
        "status": "success",
        "workers": [
            {
                "id": w.id,
                "telegram_id": w.telegram_id,
                "name": w.name,
                "role": w.role.value,
                "is_active": w.is_active,
                "daily_limit": w.daily_limit,
                "remaining_daily": w.remaining_daily,
                "referrals_count": w.referrals_count,
                "codes_created": w.codes_created,
                "codes_activated": w.codes_activated,
                "total_distributed": w.total_distributed,
                "created_at": w.created_at.isoformat()
            }
            for w in workers
        ]
    })


class AddWorkerRequest(BaseModel):
    telegram_id: str
    name: str
    role: str = "worker"


@router.post("/workers/add")
async def add_worker(
    data: AddWorkerRequest,
    token: str = Query(...),
    db: AsyncSession = Depends(get_db)
):
    """Добавить нового воркера"""
    
    admin_id = await get_current_admin(token, db)
    
    # Проверяем, не существует ли уже
    stmt = select(Worker).where(Worker.telegram_id == data.telegram_id)
    result = await db.execute(stmt)
    existing = result.scalars().first()
    
    if existing:
        raise HTTPException(status_code=400, detail="Worker already exists")
    
    # Определяем роль
    try:
        role = WorkerRole[data.role.upper()]
    except KeyError:
        raise HTTPException(status_code=400, detail="Invalid role")
    
    # Определяем лимит
    limits = {
        WorkerRole.WORKER: 10000,
        WorkerRole.ADMIN: 1000000
    }
    
    worker = Worker(
        telegram_id=data.telegram_id,
        user_id=data.telegram_id,
        name=data.name,
        role=role,
        daily_limit=limits[role],
        remaining_daily=limits[role],
        approved_by=str(admin_id),
        approved_at=datetime.utcnow(),
        is_active=True
    )
    
    db.add(worker)
    await db.commit()
    await db.refresh(worker)
    
    logger.log_activity(
        str(admin_id),
        "admin",
        "worker_added",
        "success",
        {"worker_id": data.telegram_id, "role": data.role}
    )
    
    return JSONResponse({
        "status": "success",
        "message": "Worker added successfully",
        "worker": {
            "id": worker.id,
            "telegram_id": worker.telegram_id,
            "role": worker.role.value
        }
    })


@router.delete("/workers/{worker_id}")
async def remove_worker(
    worker_id: int,
    token: str = Query(...),
    db: AsyncSession = Depends(get_db)
):
    """Удалить воркера"""
    
    admin_id = await get_current_admin(token, db)
    
    stmt = select(Worker).where(Worker.id == worker_id)
    result = await db.execute(stmt)
    worker = result.scalars().first()
    
    if not worker:
        raise HTTPException(status_code=404, detail="Worker not found")
    
    worker.is_active = False
    await db.commit()
    
    logger.log_activity(
        str(admin_id),
        "admin",
        "worker_removed",
        "success",
        {"worker_id": worker.telegram_id}
    )
    
    return JSONResponse({
        "status": "success",
        "message": "Worker removed successfully"
    })


# ============================================================================
# СТАТИСТИКА
# ============================================================================

@router.get("/stats/overview")
async def get_overview_stats(
    token: str = Query(...),
    db: AsyncSession = Depends(get_db)
):
    """Получить общую статистику"""
    
    await get_current_admin(token, db)
    
    # Всего пользователей
    stmt = select(func.count(User.id))
    result = await db.execute(stmt)
    total_users = result.scalar() or 0
    
    # Активных пользователей
    stmt = select(func.count(User.id)).where(User.is_active == True)
    result = await db.execute(stmt)
    active_users = result.scalar() or 0
    
    # Всего воркеров
    stmt = select(func.count(Worker.id))
    result = await db.execute(stmt)
    total_workers = result.scalar() or 0
    
    # Активных воркеров
    stmt = select(func.count(Worker.id)).where(Worker.is_active == True)
    result = await db.execute(stmt)
    active_workers = result.scalar() or 0
    
    # Всего передано подарков
    stmt = select(func.count(GiftTransfer.id)).where(GiftTransfer.status == "completed")
    result = await db.execute(stmt)
    total_transfers = result.scalar() or 0
    
    # Общая стоимость в звездах
    stmt = select(func.sum(GiftTransfer.gift_value_stars)).where(GiftTransfer.status == "completed")
    result = await db.execute(stmt)
    total_stars = result.scalar() or 0
    
    return JSONResponse({
        "status": "success",
        "stats": {
            "total_users": total_users,
            "active_users": active_users,
            "total_workers": total_workers,
            "active_workers": active_workers,
            "total_transfers": total_transfers,
            "total_stars_value": total_stars
        }
    })


# ============================================================================
# РАССЫЛКА
# ============================================================================

class BroadcastRequest(BaseModel):
    message_text: str
    photo_url: Optional[str] = None
    button_text: Optional[str] = None
    button_url: Optional[str] = None


@router.post("/broadcast/preview")
async def preview_broadcast(
    data: BroadcastRequest,
    token: str = Query(...),
    db: AsyncSession = Depends(get_db)
):
    """Предпросмотр рассылки"""
    
    admin_id = await get_current_admin(token, db)
    
    # Подсчитываем количество пользователей
    stmt = select(func.count(User.id)).where(User.is_active == True)
    result = await db.execute(stmt)
    total_users = result.scalar() or 0
    
    # Отправляем предпросмотр админу
    from app.bot import bot
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    
    try:
        # Создаем клавиатуру если есть кнопка
        keyboard = None
        if data.button_text and data.button_url:
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=data.button_text, url=data.button_url)]
            ])
        
        preview_text = f"📢 **ПРЕДПРОСМОТР РАССЫЛКИ**\n\n{data.message_text}\n\n---\n👥 Получателей: {total_users}"
        
        if data.photo_url:
            await bot.send_photo(
                chat_id=admin_id,
                photo=data.photo_url,
                caption=preview_text,
                reply_markup=keyboard,
                parse_mode="Markdown"
            )
        else:
            await bot.send_message(
                chat_id=admin_id,
                text=preview_text,
                reply_markup=keyboard,
                parse_mode="Markdown"
            )
    except Exception as e:
        logger.error(f"Failed to send preview: {e}")
    
    return JSONResponse({
        "status": "success",
        "preview": {
            "message_text": data.message_text,
            "photo_url": data.photo_url,
            "button_text": data.button_text,
            "button_url": data.button_url,
            "total_recipients": total_users
        }
    })


@router.post("/broadcast/send")
async def send_broadcast(
    data: BroadcastRequest,
    token: str = Query(...),
    db: AsyncSession = Depends(get_db)
):
    """Отправить рассылку всем пользователям"""
    
    admin_id = await get_current_admin(token, db)
    
    # Создаем запись о рассылке
    broadcast = Broadcast(
        admin_id=str(admin_id),
        message_text=data.message_text,
        photo_url=data.photo_url,
        button_text=data.button_text,
        button_url=data.button_url,
        status="pending",
        started_at=datetime.utcnow()
    )
    
    db.add(broadcast)
    await db.commit()
    await db.refresh(broadcast)
    
    # Получаем всех активных пользователей
    stmt = select(User).where(User.is_active == True)
    result = await db.execute(stmt)
    users = result.scalars().all()
    
    broadcast.total_users = len(users)
    await db.commit()
    
    # Запускаем отправку в фоне
    import asyncio
    from app.handlers.bot import send_broadcast_message
    
    asyncio.create_task(
        send_broadcast_message(
            broadcast_id=broadcast.id,
            text=data.message_text,
            photo=data.photo_url,
            button_text=data.button_text,
            button_url=data.button_url
        )
    )
    
    logger.log_activity(
        str(admin_id),
        "admin",
        "broadcast_started",
        "success",
        {"broadcast_id": broadcast.id, "total_users": len(users)}
    )
    
    return JSONResponse({
        "status": "success",
        "message": "Broadcast started",
        "broadcast_id": broadcast.id,
        "total_users": len(users)
    })


@router.get("/broadcast/{broadcast_id}/status")
async def get_broadcast_status(
    broadcast_id: int,
    token: str = Query(...),
    db: AsyncSession = Depends(get_db)
):
    """Получить статус рассылки"""
    
    await get_current_admin(token, db)
    
    stmt = select(Broadcast).where(Broadcast.id == broadcast_id)
    result = await db.execute(stmt)
    broadcast = result.scalars().first()
    
    if not broadcast:
        raise HTTPException(status_code=404, detail="Broadcast not found")
    
    return JSONResponse({
        "status": "success",
        "broadcast": {
            "id": broadcast.id,
            "status": broadcast.status,
            "total_users": broadcast.total_users,
            "sent_count": broadcast.sent_count,
            "failed_count": broadcast.failed_count,
            "started_at": broadcast.started_at.isoformat() if broadcast.started_at else None,
            "completed_at": broadcast.completed_at.isoformat() if broadcast.completed_at else None
        }
    })
