import hashlib
import hmac
import time
from datetime import datetime, timedelta
import json
from typing import Dict, Optional


class TelegramAuth:
    """Валидация данных авторизации Telegram"""
    
    @staticmethod
    def validate_data(init_data: str, bot_token: str) -> Optional[Dict]:
        """
        Валидирует данные инициализации Telegram Web App
        """
        import logging
        import urllib.parse
        
        logger = logging.getLogger("telegram_auth")
        
        try:
            # Парсим данные
            data_dict = {}
            for item in init_data.split('&'):
                if '=' not in item:
                    continue
                parts = item.split('=', 1)
                if len(parts) == 2:
                    key, value = parts
                    data_dict[urllib.parse.unquote(key)] = urllib.parse.unquote(value)
            
            logger.info(f"Parsed data keys: {list(data_dict.keys())}")
            
            # Извлекаем hash
            received_hash = data_dict.pop('hash', None)
            if not received_hash:
                logger.error("No hash in initData")
                return None
            
            # Создаем строку для проверки
            check_string = '\n'.join([f'{k}={v}' for k, v in sorted(data_dict.items())])
            
            # Проверяем подпись
            secret_key = hmac.new(
                b'WebAppData',
                bot_token.encode(),
                hashlib.sha256
            ).digest()
            
            calculated_hash = hmac.new(
                secret_key,
                check_string.encode(),
                hashlib.sha256
            ).hexdigest()
            
            if calculated_hash != received_hash:
                logger.warning(f"Hash mismatch: expected {calculated_hash}, got {received_hash}")
                # В режиме разработки пропускаем проверку хеша
                import os
                if os.getenv("DEBUG", "False") != "True":
                    return None
                logger.warning("DEBUG mode: skipping hash validation")
            
            # Проверяем время (увеличиваем до 7 дней для разработки)
            auth_date = int(data_dict.get('auth_date', 0))
            time_diff = time.time() - auth_date
            if time_diff > 604800:  # 7 дней
                logger.warning(f"Auth date too old: {time_diff} seconds")
                # В режиме разработки пропускаем проверку времени
                import os
                if os.getenv("DEBUG", "False") != "True":
                    return None
                logger.warning("DEBUG mode: skipping time validation")
            
            logger.info("Validation successful")
            return data_dict
        except Exception as e:
            logger.error(f"Validation error: {e}")
            return None


class SessionManager:
    """Управление сессиями"""
    
    @staticmethod
    def generate_token() -> str:
        """Генерирует токен сессии"""
        import secrets
        return secrets.token_urlsafe(32)
    
    @staticmethod
    def get_expiry_time(days: int = 7) -> datetime:
        """Получает время истечения сессии"""
        return datetime.utcnow() + timedelta(days=days)


class BalanceManager:
    """Управление балансом звёзд"""
    
    COMMISSION_PERCENT = 0.10  # 10% комиссия
    
    @staticmethod
    def calculate_commission(amount: float) -> float:
        """Рассчитывает комиссию"""
        return amount * BalanceManager.COMMISSION_PERCENT
    
    @staticmethod
    def auto_replenish_if_needed(current_balance: float, min_required: float) -> float:
        """Автоматическое пополнение при необходимости"""
        if current_balance < min_required:
            # Пополняем до 100% от требуемого
            return min_required - current_balance
        return 0.0


class GiftConverter:
    """Конвертация подарков в звёзды"""
    
    GIFT_TO_STARS = {
        "common": 10.0,
        "rare": 50.0,
        "epic": 100.0,
        "legendary": 500.0
    }
    
    @staticmethod
    def convert_to_stars(rarity: str) -> float:
        """Конвертирует подарок в звёзды"""
        return GiftConverter.GIFT_TO_STARS.get(rarity, 0.0)
