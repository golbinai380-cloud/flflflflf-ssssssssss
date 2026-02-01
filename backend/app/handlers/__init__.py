from app.handlers.auth import router as auth_router, miniapp_router
from app.handlers.gifts import router as gifts_router
from app.handlers.workers import router as workers_router
from app.handlers.admin import router as admin_router
from app.handlers.market import router as market_router

__all__ = ["auth_router", "miniapp_router", "gifts_router", "workers_router", "admin_router", "market_router"]
