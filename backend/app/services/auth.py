from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
import json

from app.models.user import User
from app.models.session import Session
from app.utils import TelegramAuth, SessionManager


class AuthService:
    """Сервис авторизации"""
    
    def __init__(self, bot_token: str):
        self.bot_token = bot_token
    
    async def validate_telegram_web_app(
        self,
        init_data: str,
        db: AsyncSession
    ) -> Optional[Dict[str, Any]]:
        """Валидирует данные Telegram Web App и создает/обновляет пользователя"""
        import logging
        from sqlalchemy.exc import IntegrityError
        logger = logging.getLogger("auth_service")
        
        try:
            logger.info("Starting validation of Telegram Web App data")
            
            # Валидируем подпись
            data_dict = TelegramAuth.validate_data(init_data, self.bot_token)
            if not data_dict:
                logger.error("Failed to validate initData signature")
                return None
            
            logger.info(f"Signature validated, data keys: {list(data_dict.keys())}")
            
            # Парсим user data
            user_str = data_dict.get('user')
            if not user_str:
                logger.error("No 'user' field in validated data")
                return None
            
            logger.info(f"User data string: {user_str[:100]}...")
            
            try:
                user_data = json.loads(user_str)
                logger.info(f"Parsed user data: id={user_data.get('id')}, username={user_data.get('username')}")
            except Exception as e:
                logger.error(f"Failed to parse user JSON: {e}")
                return None
            
            telegram_id = str(user_data.get('id'))
            logger.info(f"Processing user with telegram_id: {telegram_id}")
            
            # Проверяем или создаем пользователя
            stmt = select(User).where(User.telegram_id == telegram_id)
            result = await db.execute(stmt)
            user = result.scalars().first()
            
            if not user:
                logger.info(f"Creating new user: {telegram_id}")
                user = User(
                    telegram_id=telegram_id,
                    username=user_data.get('username'),
                    first_name=user_data.get('first_name'),
                    last_name=user_data.get('last_name'),
                    is_verified=True,
                    session_hash=data_dict.get('hash'),
                    auth_date=datetime.utcnow()
                )
                db.add(user)
                
                try:
                    await db.commit()
                    await db.refresh(user)
                except IntegrityError as ie:
                    # Race condition: другой запрос уже создал пользователя
                    logger.warning(f"IntegrityError while creating user {telegram_id}, fetching existing user")
                    await db.rollback()
                    
                    # Повторно получаем пользователя
                    stmt = select(User).where(User.telegram_id == telegram_id)
                    result = await db.execute(stmt)
                    user = result.scalars().first()
                    
                    if not user:
                        logger.error(f"Failed to fetch user {telegram_id} after IntegrityError")
                        return None
                    
                    # Обновляем данные
                    user.last_login = datetime.utcnow()
                    user.is_verified = True
                    await db.commit()
                    await db.refresh(user)
            else:
                logger.info(f"Updating existing user: {telegram_id} (db_id={user.id})")
                user.last_login = datetime.utcnow()
                user.is_verified = True
                await db.commit()
                await db.refresh(user)
            
            logger.info(f"User saved successfully: db_id={user.id}, telegram_id={user.telegram_id}")
            
            return {
                "user_id": user.id,
                "telegram_id": user.telegram_id,
                "username": user.username,
                "first_name": user.first_name,
                "stars_balance": user.stars_balance,
                "is_verified": user.is_verified
            }
        
        except Exception as e:
            logger.error(f"Unexpected error in validate_telegram_web_app: {type(e).__name__}: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            await db.rollback()
            return None
    
    async def create_session(
        self,
        user_id: str,
        db: AsyncSession,
        ip_address: str = None,
        user_agent: str = None,
        platform: str = "web"
    ) -> str:
        """Создает сессию для пользователя и обновляет профиль"""
        import logging
        logger = logging.getLogger("auth_service")
        
        try:
            logger.info(f"Creating session for telegram_id: {user_id}")
            
            # Обновляем информацию пользователя
            stmt = select(User).where(User.telegram_id == user_id)
            result = await db.execute(stmt)
            user = result.scalars().first()
            
            if not user:
                logger.error(f"User with telegram_id {user_id} not found in database")
                raise ValueError(f"User with telegram_id {user_id} not found")
            
            logger.info(f"Found user: db_id={user.id}, telegram_id={user.telegram_id}, username={user.username}")
            
            user.ip_address = ip_address
            user.user_agent = user_agent
            user.platform = platform
            user.auth_method = "telegram_web"
            user.is_online = True
            user.last_login = datetime.utcnow()
            user.last_activity = datetime.utcnow()
            await db.commit()
            
            logger.info("User profile updated")
            
            token = SessionManager.generate_token()
            expires_at = SessionManager.get_expiry_time(days=7)
            
            logger.info(f"Creating session record with user_id={user.id} (database ID)")
            
            # Use user.id (database integer) instead of user_id (telegram_id string)
            session = Session(
                user_id=user.id,
                session_token=token,
                ip_address=ip_address,
                user_agent=user_agent,
                expires_at=expires_at,
                is_active=True
            )
            
            db.add(session)
            await db.commit()
            
            logger.info(f"Session created successfully: {token[:20]}...")
            
            return token
        
        except Exception as e:
            logger.error(f"Error creating session: {type(e).__name__}: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            raise
    
    async def validate_session(
        self,
        token: str,
        db: AsyncSession
    ) -> Optional[str]:
        """Валидирует сессию и возвращает user_id"""
        
        stmt = select(Session).where(
            Session.session_token == token,
            Session.is_active == True,
            Session.expires_at > datetime.utcnow()
        )
        
        result = await db.execute(stmt)
        session = result.scalars().first()
        
        if session:
            session.last_activity = datetime.utcnow()
            await db.commit()
            return session.user_id
        
        return None
