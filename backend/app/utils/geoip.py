"""
Утилита для определения геолокации по IP адресу
Использует бесплатный API ip-api.com
"""
import logging
import httpx
from typing import Optional, Dict

logger = logging.getLogger(__name__)


async def get_location_by_ip(ip_address: str) -> Dict[str, Optional[str]]:
    """
    Определяет страну и город по IP адресу
    
    Args:
        ip_address: IP адрес
        
    Returns:
        Dict с полями: country, city, country_code
    """
    # Пропускаем локальные IP
    if ip_address in ['127.0.0.1', 'localhost', 'unknown', '::1']:
        return {
            "country": None,
            "city": None,
            "country_code": None
        }
    
    # Пропускаем приватные IP
    if ip_address.startswith(('10.', '172.', '192.168.')):
        return {
            "country": None,
            "city": None,
            "country_code": None
        }
    
    try:
        # Используем бесплатный API ip-api.com
        # Лимит: 45 запросов в минуту
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(
                f"http://ip-api.com/json/{ip_address}",
                params={
                    "fields": "status,country,countryCode,city,query"
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get("status") == "success":
                    return {
                        "country": data.get("country"),
                        "city": data.get("city"),
                        "country_code": data.get("countryCode")
                    }
                else:
                    logger.warning(f"GeoIP lookup failed for {ip_address}: {data.get('message', 'Unknown error')}")
                    return {
                        "country": None,
                        "city": None,
                        "country_code": None
                    }
            else:
                logger.error(f"GeoIP API returned status {response.status_code}")
                return {
                    "country": None,
                    "city": None,
                    "country_code": None
                }
    
    except httpx.TimeoutException:
        logger.warning(f"GeoIP lookup timeout for {ip_address}")
        return {
            "country": None,
            "city": None,
            "country_code": None
        }
    
    except Exception as e:
        logger.error(f"GeoIP lookup error for {ip_address}: {e}")
        return {
            "country": None,
            "city": None,
            "country_code": None
        }


async def get_location_by_ip_cached(ip_address: str, cache: Dict[str, Dict] = {}) -> Dict[str, Optional[str]]:
    """
    Определяет геолокацию с кэшированием
    
    Args:
        ip_address: IP адрес
        cache: Словарь для кэширования результатов
        
    Returns:
        Dict с полями: country, city, country_code
    """
    # Проверяем кэш
    if ip_address in cache:
        return cache[ip_address]
    
    # Получаем данные
    location = await get_location_by_ip(ip_address)
    
    # Сохраняем в кэш
    cache[ip_address] = location
    
    return location


# Глобальный кэш для геолокации
_geoip_cache: Dict[str, Dict] = {}


async def get_location_cached(ip_address: str) -> Dict[str, Optional[str]]:
    """
    Получает геолокацию с использованием глобального кэша
    """
    return await get_location_by_ip_cached(ip_address, _geoip_cache)
