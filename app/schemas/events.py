from datetime import datetime

from pydantic import BaseModel, Field


class PaidOrderEvent(BaseModel):
    event_id: str = Field(min_length=1)
    reference: str = Field(min_length=1)
    amount: int = Field(gt=0)
    provider: str = "paystack"
    occurred_at: datetime = Field(default_factory=datetime.utcnow)
