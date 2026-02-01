from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
import os
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Создаем единый Base для всех моделей
Base = declarative_base()

# Определяем путь к базе данных
def get_database_path() -> Path:
    """Получает путь к файлу базы данных"""
    # Получаем базовую директорию (backend/)
    backend_dir = Path(__file__).parent.parent.parent
    
    # Используем database.db в backend директории
    db_path = backend_dir / "database.db"
    
    logger.info(f"📁 База данных: {db_path}")
    return db_path

# Создаем директорию если её нет
db_path = get_database_path()
db_path.parent.mkdir(parents=True, exist_ok=True)

# Формируем DATABASE_URL с абсолютным путём
_DATABASE_URL = f"sqlite+aiosqlite:///{db_path}"

# Альтернативный способ из переменной окружения (если нужна другая БД)
_ENV_DB_URL = os.getenv("DATABASE_URL")
if _ENV_DB_URL and "sqlite" not in _ENV_DB_URL:
    # Если указана неSQLite БД (PostgreSQL, MySQL и т.д.)
    _DATABASE_URL = _ENV_DB_URL
    logger.info(f"🔗 Используется внешняя БД: {_DATABASE_URL}")

DATABASE_URL = _DATABASE_URL

engine = create_async_engine(
    DATABASE_URL,
    echo=False,  # Disable SQLAlchemy query logging
    future=True,
    connect_args={
        "check_same_thread": False,
        "timeout": 30
    } if "sqlite" in DATABASE_URL else {}
)

AsyncSessionLocal = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


async def get_db():
    """Зависимость для получения сессии БД"""
    try:
        async with AsyncSessionLocal() as session:
            yield session
    except Exception as e:
        logger.error(f"❌ Ошибка получения сессии БД: {e}")
        raise


async def init_db():
    """Инициализация БД - создает таблицы если их нет"""
    try:
        logger.info("🚀 Инициализация базы данных...")
        
        # Импортируем модели
        from app.models import Base
        
        # Создаем таблицы
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        logger.info(f"✅ База данных инициализирована ({db_path})")
        
        # Проверяем что файл создан
        if "sqlite" in DATABASE_URL:
            if db_path.exists():
                size_mb = db_path.stat().st_size / (1024 * 1024)
                logger.info(f"   Файл БД создан успешно (размер: {size_mb:.2f} MB)")
            else:
                logger.warning(f"   ⚠️  Файл БД не найден в {db_path}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Ошибка инициализации БД: {e}")
        import traceback
        traceback.print_exc()
        return False


async def drop_all_tables():
    """Удаляет все таблицы (только для разработки!)"""
    try:
        from app.models import Base
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        logger.warning("⚠️  Все таблицы удалены!")
    except Exception as e:
        logger.error(f"❌ Ошибка удаления таблиц: {e}")
