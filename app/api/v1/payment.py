from fastapi import APIRouter
from fastapi.requests import Request

from app.api.dependencies import (
    dbSessionDep,
    redisSessionDep,
)
from app.service.order_srevice import order_service

router = APIRouter(prefix="/payment", tags=["Payments"])


@router.post("/paystack/webhook", summary="Paystack Webhook to verify payment")
async def paystack_webhook(request: Request, db: dbSessionDep, redis: redisSessionDep):
    return await order_service.handle_successful_payment(request, db, redis)
