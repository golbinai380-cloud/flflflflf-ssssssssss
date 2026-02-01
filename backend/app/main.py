"""
Telegram Mini App - Gift Market Backend
Полностью переписанный и оптимизированный для Telegram Mini App
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import os
import sys
import logging
from contextlib import asynccontextmanager

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Отключаем мусорные логи SQLAlchemy
logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)
logging.getLogger('sqlalchemy.pool').setLevel(logging.WARNING)

logger = logging.getLogger("miniapp")

# Загружаем .env
from dotenv import load_dotenv
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)

# Проверяем критические переменные
REQUIRED_ENV = ["TELEGRAM_BOT_TOKEN", "ADMIN_ID"]
missing = [var for var in REQUIRED_ENV if not os.getenv(var)]
if missing:
    logger.error(f"❌ Отсутствуют переменные: {', '.join(missing)}")
    logger.error(f"📝 Создайте файл {env_path} и заполните его")
    sys.exit(1)

logger.info("✅ Переменные окружения загружены")

# Импорты после проверки env
from app.database import init_db
from app.handlers import auth_router, miniapp_router, gifts_router, workers_router, admin_router, market_router
from app.handlers.worker_panel import router as worker_panel_router
from app.handlers.admin_panel import router as admin_panel_router
from app.handlers.session import router as session_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Жизненный цикл приложения"""
    # Startup
    logger.info("🚀 Запуск Telegram Mini App Backend...")
    try:
        await init_db()
        logger.info("✅ База данных инициализирована")
    except Exception as e:
        logger.error(f"❌ Ошибка БД: {e}")
        sys.exit(1)
    
    logger.info("🎉 Backend готов к работе!")
    logger.info(f"📖 Документация: http://{os.getenv('API_HOST', '0.0.0.0')}:{os.getenv('API_PORT', 8000)}/docs")
    
    yield
    
    # Shutdown
    logger.info("⏹️  Backend останавливается...")


# Создаем приложение
app = FastAPI(
    title="Telegram Mini App - Gift Market",
    description="Backend для Telegram Mini App с управлением подарками",
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS - разрешаем все для Telegram Mini App
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Telegram Mini App может приходить с разных origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)

# Определяем пути
BASE_DIR = Path(__file__).resolve().parent.parent.parent
FRONTEND_DIR = BASE_DIR
MARKET_DIR = BASE_DIR / "market"

logger.info(f"📁 BASE_DIR: {BASE_DIR}")
logger.info(f"📁 FRONTEND: {FRONTEND_DIR}")
logger.info(f"📁 MARKET: {MARKET_DIR}")

# Проверяем файлы
if not (FRONTEND_DIR / "index.html").exists():
    logger.error(f"❌ index.html не найден: {FRONTEND_DIR / 'index.html'}")
    sys.exit(1)

if not MARKET_DIR.exists():
    logger.error(f"❌ Папка market/ не найдена: {MARKET_DIR}")
    sys.exit(1)

logger.info(f"✅ index.html найден")
logger.info(f"✅ market/ найден ({len(list(MARKET_DIR.glob('*')))} файлов)")

# Подключаем API роуты ПЕРЕД статикой (чтобы API имели приоритет)
app.include_router(market_router)  # Главный роутер для Mini App
app.include_router(auth_router)
app.include_router(miniapp_router)  # MiniApp auth endpoint
app.include_router(gifts_router)
app.include_router(workers_router)
app.include_router(admin_router)
app.include_router(worker_panel_router)  # Worker Panel API
app.include_router(admin_panel_router)  # Admin Panel API
app.include_router(session_router)  # Session Management API

logger.info("✅ API роуты подключены")

# Монтируем статические файлы ПОСЛЕ роутов (чтобы API имели приоритет)
try:
    app.mount("/market", StaticFiles(directory=str(MARKET_DIR)), name="market")
    logger.info("✅ Статика /market/ подключена")
except Exception as e:
    logger.error(f"❌ Ошибка монтирования /market/: {e}")
    sys.exit(1)

# Serve specific frontend HTML files (admin/worker) without mounting the whole frontend at '/'
# This keeps the root SPA handler (app.get('/')) working while making these pages accessible.
@app.get('/admin-panel.html', response_class=HTMLResponse, include_in_schema=False)
async def serve_admin_panel(request: Request):
    try:
        admin_path = FRONTEND_DIR / 'admin-panel.html'
        if admin_path.exists():
            with open(admin_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return HTMLResponse(content=content)
    except Exception as e:
        logger.error(f"Error serving admin-panel.html: {e}")
    return HTMLResponse(content="<script>window.location.href='/'</script>", status_code=404)


@app.get('/worker-panel.html', response_class=HTMLResponse, include_in_schema=False)
async def serve_worker_panel(request: Request):
    try:
        worker_path = FRONTEND_DIR / 'worker-panel.html'
        if worker_path.exists():
            with open(worker_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return HTMLResponse(content=content)
    except Exception as e:
        logger.error(f"Error serving worker-panel.html: {e}")
    return HTMLResponse(content="<script>window.location.href='/'</script>", status_code=404)


# ============================================
# ГЛАВНАЯ СТРАНИЦА - TELEGRAM MINI APP
# ============================================

@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def serve_miniapp(request: Request):
    """
    Возвращает главную страницу Telegram Mini App
    Это единственная HTML страница - все остальное через API
    """
    try:
        index_path = FRONTEND_DIR / "index.html"
        
        # Читаем HTML
        with open(index_path, "r", encoding="utf-8") as f:
            html_content = f.read()
        
        # Логируем запрос
        user_agent = request.headers.get("user-agent", "unknown")
        is_telegram = "Telegram" in user_agent
        
        logger.info(f"📱 Запрос Mini App | Telegram: {is_telegram} | UA: {user_agent[:50]}")
        
        return HTMLResponse(
            content=html_content,
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0",
                "X-Content-Type-Options": "nosniff",
                "X-Frame-Options": "ALLOWALL",  # Разрешаем iframe для Telegram
                "Content-Security-Policy": "frame-ancestors *"  # Разрешаем загрузку в iframe
            }
        )
    
    except Exception as e:
        logger.error(f"❌ Ошибка загрузки index.html: {e}")
        return HTMLResponse(
            content=f"<h1>Error</h1><p>{str(e)}</p>",
            status_code=500
        )


# ============================================
# ДИАГНОСТИКА
# ============================================

@app.get("/api/health")
async def health_check():
    """Проверка здоровья API"""
    return {
        "status": "healthy",
        "service": "telegram-miniapp-backend",
        "version": "2.0.0"
    }


@app.get("/api/info")
async def app_info(request: Request):
    """Информация о приложении"""
    return {
        "app": "Telegram Mini App - Gift Market",
        "version": "2.0.0",
        "telegram_bot_configured": bool(os.getenv("TELEGRAM_BOT_TOKEN")),
        "user_agent": request.headers.get("user-agent", "unknown"),
        "is_telegram": "Telegram" in request.headers.get("user-agent", ""),
        "endpoints": {
            "main": "/",
            "health": "/api/health",
            "docs": "/docs",
            "market_api": "/market/*"
        }
    }


@app.get("/api/debug/paths")
async def debug_paths():
    """Отладка путей (только для разработки)"""
    if os.getenv("DEBUG", "False") != "True":
        return {"error": "Debug mode disabled"}
    
    return {
        "base_dir": str(BASE_DIR),
        "frontend_dir": str(FRONTEND_DIR),
        "market_dir": str(MARKET_DIR),
        "index_exists": (FRONTEND_DIR / "index.html").exists(),
        "market_exists": MARKET_DIR.exists(),
        "market_files": [f.name for f in MARKET_DIR.glob("*")] if MARKET_DIR.exists() else []
    }


# ============================================
# ОБРАБОТКА ОШИБОК
# ============================================

@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    """Обработчик 404 ошибок"""
    logger.warning(f"404: {request.url.path}")
    
    # Если это API запрос - возвращаем JSON
    if request.url.path.startswith("/api/") or request.url.path.startswith("/market/"):
        return JSONResponse(
            status_code=404,
            content={"error": "Not found", "path": request.url.path}
        )
    
    # Для остальных - редирект на главную (SPA)
    return HTMLResponse(
        content="<script>window.location.href='/';</script>",
        status_code=404
    )


@app.exception_handler(500)
async def server_error_handler(request: Request, exc):
    """Обработчик 500 ошибок"""
    logger.error(f"500: {request.url.path} | {exc}")
    
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "message": str(exc)}
    )


# ============================================
# ЗАПУСК
# ============================================

if __name__ == "__main__":
    import uvicorn
    
    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", 8000))
    debug = os.getenv("DEBUG", "True") == "True"
    
    logger.info(f"🚀 Запуск на {host}:{port}")
    logger.info(f"🔧 Debug mode: {debug}")
    
    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=debug,
        log_level="info"
    )
