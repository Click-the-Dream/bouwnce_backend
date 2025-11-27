from typing import Annotated

from fastapi import APIRouter, Query
from fastapi.requests import Request

from app.api.dependencies import (
    CurrentActiveUser,
    PaystackSignature,
    dbSessionDep,
    redisSessionDep,
)
from app.service.order_srevice import order_service

router = APIRouter(prefix="/payment", tags=["Payments"])


@router.post("/paystack/webhook", summary="Paystack Webhook to verify payment")
async def paystack_webhook(
    _: PaystackSignature, request: Request, db: dbSessionDep, redis: redisSessionDep
):
    return await order_service.handle_successful_payment(request, db, redis)


@router.get(
    "/verify", summary="Verify Payment using reference token from payment gateway"
)
async def verify_payment(
    db: dbSessionDep,
    current_user: CurrentActiveUser,
    redis: redisSessionDep,
    referenceToken: Annotated[str, Query(..., examples=["qTPrJoy9Bx"])],
):
    return order_service.verify_payment(current_user, referenceToken, redis, db)
