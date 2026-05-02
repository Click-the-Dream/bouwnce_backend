from fastapi import APIRouter, HTTPException, status
from fastapi.requests import Request
from pydantic import BaseModel, Field

from app.api.dependencies import (
    dbSessionDep,
    redisSessionDep,
)
from app.core.config import settings
from app.service.order_srevice import order_service

router = APIRouter(prefix="/payment", tags=["Payments"])

class SimulatePaystackChargeSuccessRequest(BaseModel):
    reference: str = Field(min_length=1)
    amount_kobo: int = Field(gt=0)
    event_id: str | None = None


@router.post("/paystack/webhook", summary="Paystack Webhook to verify payment")
async def paystack_webhook(request: Request, db: dbSessionDep, redis: redisSessionDep):
    return await order_service.handle_successful_payment(request, db, redis)


@router.post(
    "/paystack/simulate-charge-success",
    summary="Simulate paystack charge.success (dev/test only)",
)
async def simulate_paystack_charge_success(
    payload: SimulatePaystackChargeSuccessRequest,
    db: dbSessionDep,
    redis: redisSessionDep,
):
    if not settings.ALLOW_TEST_PAYSTACK_WEBHOOK:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    return await order_service.queue_paid_order(
        reference=payload.reference,
        amount_kobo=payload.amount_kobo,
        event_id=payload.event_id,
        db=db,
        redis=redis,
    )
