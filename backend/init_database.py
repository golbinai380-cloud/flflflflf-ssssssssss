#!/usr/bin/env python3
"""
🔧 ИНИЦИАЛИЗАЦИЯ БАЗЫ ДАННЫХ
Создает все таблицы и начальные данные
Запускается автоматически при старте приложения
"""
import asyncio
import os
import sys
from pathlib import Path

# Добавляем путь к backend в sys.path
backend_path = Path(__file__).parent
sys.path.insert(0, str(backend_path))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.future import select

# Импортируем все модели
from app.models.user import User, Base as UserBase
from app.models.worker import Worker, WorkerRole, UserWorkerBinding, Base as WorkerBase
from app.models.session import Session, Base as SessionBase
from app.models.telegram_session import TelegramSession, IPHistory, Base as TelegramSessionBase
from app.models.gift import Gift, Base as GiftBase
from app.models.analytics import ActivityLog, Base as AnalyticsBase


async def init_database():
    """Инициализирует базу данных"""
    
    print("=" * 70)
    print("🔧 ИНИЦИАЛИЗАЦИЯ БАЗЫ ДАННЫХ")
    print("=" * 70)
    
    # Создаем подключение к БД
    database_url = "sqlite+aiosqlite:///./database.db"
    engine = create_async_engine(database_url, echo=False)
    
    print("\n📋 Шаг 1: Создание таблиц...")
    
    # Создаем все таблицы
    async with engine.begin() as conn:
        # Создаем таблицы для всех моделей
        await conn.run_sync(UserBase.metadata.create_all)
        await conn.run_sync(WorkerBase.metadata.create_all)
        await conn.run_sync(SessionBase.metadata.create_all)
        await conn.run_sync(TelegramSessionBase.metadata.create_all)
        await conn.run_sync(GiftBase.metadata.create_all)
        await conn.run_sync(AnalyticsBase.metadata.create_all)
    
    print("✅ Таблицы созданы:")
    print("   - users (пользователи)")
    print("   - workers (воркеры)")
    print("   - user_worker_bindings (привязки пользователей к воркерам)")
    print("   - sessions (сессии)")
    print("   - telegram_sessions (Telegram сессии)")
    print("   - ip_history (история IP адресов)")
    print("   - gifts (подарки)")
    print("   - analytics (аналитика)")
    
    # Создаем сессию для работы с БД
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    print("\n📋 Шаг 2: Проверка администратора...")
    
    async with async_session() as db:
        # Получаем ADMIN_ID из .env
        admin_id = str(os.getenv("ADMIN_ID", "0"))
        admin_username = os.getenv("ADMIN_USERNAME", "admin")
        
        if admin_id == "0":
            print("⚠️  ADMIN_ID не установлен в .env")
            print("   Установите ADMIN_ID в файле backend/.env")
            return
        
        print(f"🔍 Проверка администратора: {admin_id} (@{admin_username})")
        
        # Проверяем Worker запись
        stmt = select(Worker).where(Worker.telegram_id == admin_id)
        result = await db.execute(stmt)
        worker = result.scalars().first()
        
        if worker:
            print(f"✅ Worker найден: id={worker.id}, role={worker.role}, is_active={worker.is_active}")
            
            # Обновляем если нужно
            updated = False
            if worker.role != WorkerRole.ADMIN:
                print(f"   ⚠️  Обновление роли: {worker.role} → ADMIN")
                worker.role = WorkerRole.ADMIN
                updated = True
            
            if not worker.is_active:
                print(f"   ⚠️  Активация воркера")
                worker.is_active = True
                updated = True
            
            if updated:
                await db.commit()
                print(f"   ✅ Worker обновлен")
        else:
            print(f"⚠️  Worker не найден, создаем...")
            
            # Создаем Worker запись
            new_worker = Worker(
                telegram_id=admin_id,
                name=admin_username or f"admin_{admin_id}",
                role=WorkerRole.ADMIN,
                is_active=True
            )
            db.add(new_worker)
            await db.commit()
            await db.refresh(new_worker)
            
            print(f"✅ Worker создан:")
            print(f"   - ID: {new_worker.id}")
            print(f"   - Telegram ID: {new_worker.telegram_id}")
            print(f"   - Role: {new_worker.role}")
            print(f"   - Active: {new_worker.is_active}")
        
        # Проверяем User запись
        stmt = select(User).where(User.telegram_id == admin_id)
        result = await db.execute(stmt)
        user = result.scalars().first()
        
        if user:
            print(f"✅ User найден: id={user.id}, username={user.username}")
        else:
            print(f"ℹ️  User не найден")
            print(f"   User будет создан автоматически при первом входе в Mini App")
    
    print("\n📋 Шаг 3: Проверка целостности данных...")
    
    async with async_session() as db:
        # Подсчитываем записи
        stmt = select(User)
        result = await db.execute(stmt)
        users_count = len(result.scalars().all())
        
        stmt = select(Worker)
        result = await db.execute(stmt)
        workers_count = len(result.scalars().all())
        
        stmt = select(Session)
        result = await db.execute(stmt)
        sessions_count = len(result.scalars().all())
        
        print(f"✅ Статистика базы данных:")
        print(f"   - Пользователей: {users_count}")
        print(f"   - Воркеров: {workers_count}")
        print(f"   - Активных сессий: {sessions_count}")
    
    await engine.dispose()
    
    print("\n" + "=" * 70)
    print("✅ ИНИЦИАЛИЗАЦИЯ ЗАВЕРШЕНА")
    print("=" * 70)
    print("\n💡 База данных готова к работе!")
    print(f"   Файл: {Path('database.db').absolute()}")
    print(f"   Администратор: {admin_id} (@{admin_username})")
    print()


if __name__ == "__main__":
    # Загружаем .env
    from dotenv import load_dotenv
    load_dotenv()
    
    try:
        asyncio.run(init_database())
    except KeyboardInterrupt:
        print("\n\n⚠️  Инициализация прервана пользователем")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ ОШИБКА ИНИЦИАЛИЗАЦИИ: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
