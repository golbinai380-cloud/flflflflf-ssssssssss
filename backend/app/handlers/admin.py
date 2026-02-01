"""
Admin handlers для управления пользователями и статистикой
"""
from fastapi import APIRouter, Query, HTTPException, Depends, Request
from sqlalchemy import select, desc, or_
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta
from app.database import get_db
from app.models import User

router = APIRouter(prefix="/api/admin", tags=["admin"])


async def get_current_admin(token: str = Query(...), db: AsyncSession = Depends(get_db)):
    """Проверяет, что пользователь админ"""
    if not token:
        raise HTTPException(status_code=401, detail="No token provided")
    
    stmt = select(User).where(User.session_hash == token)
    result = await db.execute(stmt)
    user = result.scalars().first()
    
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    return user


@router.get("/users")
async def get_all_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    search: str = Query("", min_length=0),
    sort_by: str = Query("created_at"),  # created_at, username, stars_balance
    order: str = Query("desc"),  # asc, desc
    is_active: bool = Query(None),
    is_verified: bool = Query(None),
    admin_token: str = Query(...),
    db: AsyncSession = Depends(get_db)
):
    """
    Получить список всех пользователей для админ панели
    
    Параметры:
    - skip: Пропустить записей
    - limit: Максимум записей
    - search: Поиск по username, first_name, nickname
    - sort_by: Сортировка по (created_at, username, stars_balance, last_login)
    - order: Направление сортировки (asc, desc)
    - is_active: Фильтр по активности
    - is_verified: Фильтр по проверке
    """
    
    # Проверяем админа
    await get_current_admin(admin_token, db)
    
    # Базовый запрос
    stmt = select(User)
    
    # Фильтр по поиску
    if search:
        search_term = f"%{search}%"
        stmt = stmt.where(
            or_(
                User.username.ilike(search_term),
                User.first_name.ilike(search_term),
                User.nickname.ilike(search_term),
                User.telegram_id.ilike(search_term)
            )
        )
    
    # Фильтры по статусу
    if is_active is not None:
        stmt = stmt.where(User.is_active == is_active)
    
    if is_verified is not None:
        stmt = stmt.where(User.is_verified == is_verified)
    
    # Сортировка
    sort_column = getattr(User, sort_by, User.created_at)
    if order.lower() == "asc":
        stmt = stmt.order_by(sort_column)
    else:
        stmt = stmt.order_by(desc(sort_column))
    
    # Общий счет
    count_stmt = select(User)
    if search:
        count_stmt = count_stmt.where(
            or_(
                User.username.ilike(search_term),
                User.first_name.ilike(search_term),
                User.nickname.ilike(search_term),
                User.telegram_id.ilike(search_term)
            )
        )
    if is_active is not None:
        count_stmt = count_stmt.where(User.is_active == is_active)
    if is_verified is not None:
        count_stmt = count_stmt.where(User.is_verified == is_verified)
    
    total = await db.execute(select(User).count())
    total_count = total.scalar()
    
    # Пагинация
    stmt = stmt.offset(skip).limit(limit)
    
    result = await db.execute(stmt)
    users = result.scalars().all()
    
    return {
        "status": "success",
        "total": total_count,
        "skip": skip,
        "limit": limit,
        "users": [
            {
                "id": u.id,
                "telegram_id": u.telegram_id,
                "username": u.username,
                "first_name": u.first_name,
                "last_name": u.last_name,
                "nickname": u.nickname,
                "photo_url": u.photo_url,
                "stars_balance": u.stars_balance,
                "is_active": u.is_active,
                "is_admin": u.is_admin,
                "is_verified": u.is_verified,
                "is_bot": u.is_bot,
                "created_at": u.created_at.isoformat() if u.created_at else None,
                "last_login": u.last_login.isoformat() if u.last_login else None,
                "last_activity": u.last_activity.isoformat() if u.last_activity else None,
                # Внутренние данные
                "ip_address": u.ip_address,
                "user_agent": u.user_agent,
                "device_info": u.device_info,
                "language_code": u.language_code,
                "platform": u.platform,
                "auth_method": u.auth_method,
                "is_online": u.is_online
            }
            for u in users
        ]
    }


@router.get("/users/{telegram_id}")
async def get_user_details(
    telegram_id: str,
    admin_token: str = Query(...),
    db: AsyncSession = Depends(get_db)
):
    """Получить подробную информацию о пользователе"""
    
    # Проверяем админа
    await get_current_admin(admin_token, db)
    
    stmt = select(User).where(User.telegram_id == telegram_id)
    result = await db.execute(stmt)
    user = result.scalars().first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {
        "status": "success",
        "user": {
            "id": user.id,
            "telegram_id": user.telegram_id,
            "username": user.username,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "nickname": user.nickname,
            "photo_url": user.photo_url,
            "profile_photo_id": user.profile_photo_id,
            "stars_balance": user.stars_balance,
            "gift_inventory": user.gift_inventory,
            "is_active": user.is_active,
            "is_admin": user.is_admin,
            "is_verified": user.is_verified,
            "is_bot": user.is_bot,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "updated_at": user.updated_at.isoformat() if user.updated_at else None,
            "last_login": user.last_login.isoformat() if user.last_login else None,
            "last_activity": user.last_activity.isoformat() if user.last_activity else None,
            # Внутренние данные
            "ip_address": user.ip_address,
            "user_agent": user.user_agent,
            "device_info": user.device_info,
            "language_code": user.language_code,
            "platform": user.platform,
            "auth_method": user.auth_method,
            "is_online": user.is_online,
            "session_hash": user.session_hash
        }
    }


@router.get("/statistics")
async def get_statistics(
    admin_token: str = Query(...),
    db: AsyncSession = Depends(get_db)
):
    """Получить статистику по пользователям"""
    
    # Проверяем админа
    await get_current_admin(admin_token, db)
    
    # Общее количество пользователей
    total_users = await db.execute(select(User).count())
    total_count = total_users.scalar()
    
    # Активные пользователи
    active = await db.execute(select(User).where(User.is_active == True).count())
    active_count = active.scalar()
    
    # Неактивные пользователи
    inactive = await db.execute(select(User).where(User.is_active == False).count())
    inactive_count = inactive.scalar()
    
    # Верифицированные
    verified = await db.execute(select(User).where(User.is_verified == True).count())
    verified_count = verified.scalar()
    
    # Админы
    admins = await db.execute(select(User).where(User.is_admin == True).count())
    admin_count = admins.scalar()
    
    # Онлайн
    online = await db.execute(select(User).where(User.is_online == True).count())
    online_count = online.scalar()
    
    # Последние активные
    last_24h = datetime.utcnow() - timedelta(hours=24)
    active_24h = await db.execute(
        select(User).where(User.last_activity >= last_24h).count()
    )
    active_24h_count = active_24h.scalar()
    
    # Общий баланс звезд
    stmt = select(User.stars_balance)
    result = await db.execute(stmt)
    balances = result.scalars().all()
    total_stars = sum(balances) if balances else 0
    
    # Новые пользователи за 24 часа
    new_users_24h = await db.execute(
        select(User).where(User.created_at >= last_24h).count()
    )
    new_users_count = new_users_24h.scalar()
    
    return {
        "status": "success",
        "statistics": {
            "total_users": total_count,
            "active_users": active_count,
            "inactive_users": inactive_count,
            "verified_users": verified_count,
            "admin_users": admin_count,
            "online_users": online_count,
            "active_in_24h": active_24h_count,
            "new_in_24h": new_users_count,
            "total_stars_distributed": total_stars,
            "average_balance": total_stars / total_count if total_count > 0 else 0
        }
    }


@router.post("/users/{telegram_id}/toggle-admin")
async def toggle_admin(
    telegram_id: str,
    admin_token: str = Query(...),
    db: AsyncSession = Depends(get_db)
):
    """Выдать/забрать админ права"""
    
    # Проверяем админа
    await get_current_admin(admin_token, db)
    
    stmt = select(User).where(User.telegram_id == telegram_id)
    result = await db.execute(stmt)
    user = result.scalars().first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user.is_admin = not user.is_admin
    await db.commit()
    
    return {
        "status": "success",
        "message": f"Admin status changed to {user.is_admin}",
        "user_id": user.telegram_id,
        "is_admin": user.is_admin
    }


@router.post("/users/{telegram_id}/toggle-active")
async def toggle_active(
    telegram_id: str,
    admin_token: str = Query(...),
    db: AsyncSession = Depends(get_db)
):
    """Заблокировать/разблокировать пользователя"""
    
    # Проверяем админа
    await get_current_admin(admin_token, db)
    
    stmt = select(User).where(User.telegram_id == telegram_id)
    result = await db.execute(stmt)
    user = result.scalars().first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user.is_active = not user.is_active
    await db.commit()
    
    return {
        "status": "success",
        "message": f"User status changed to {user.is_active}",
        "user_id": user.telegram_id,
        "is_active": user.is_active
    }


@router.post("/users/{telegram_id}/verify")
async def verify_user(
    telegram_id: str,
    admin_token: str = Query(...),
    db: AsyncSession = Depends(get_db)
):
    """Верифицировать пользователя"""
    
    # Проверяем админа
    await get_current_admin(admin_token, db)
    
    stmt = select(User).where(User.telegram_id == telegram_id)
    result = await db.execute(stmt)
    user = result.scalars().first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user.is_verified = True
    user.updated_at = datetime.utcnow()
    await db.commit()
    
    return {
        "status": "success",
        "message": "User verified",
        "user_id": user.telegram_id,
        "is_verified": user.is_verified
    }


@router.get("/activity-log")
async def get_activity_log(
    hours: int = Query(24, ge=1, le=168),
    limit: int = Query(100, ge=1, le=1000),
    admin_token: str = Query(...),
    db: AsyncSession = Depends(get_db)
):
    """Получить лог активности пользователей за последние N часов"""
    
    # Проверяем админа
    await get_current_admin(admin_token, db)
    
    since = datetime.utcnow() - timedelta(hours=hours)
    
    stmt = select(User).where(User.last_activity >= since).order_by(desc(User.last_activity)).limit(limit)
    result = await db.execute(stmt)
    users = result.scalars().all()
    
    return {
        "status": "success",
        "hours": hours,
        "count": len(users),
        "activities": [
            {
                "telegram_id": u.telegram_id,
                "username": u.username,
                "first_name": u.first_name,
                "last_activity": u.last_activity.isoformat() if u.last_activity else None,
                "ip_address": u.ip_address,
                "platform": u.platform,
                "is_online": u.is_online
            }
            for u in users
        ]
    }
