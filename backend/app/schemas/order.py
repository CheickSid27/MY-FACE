import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.order import OrderStatus, PaymentMethod


class OrderRead(BaseModel):
    id: uuid.UUID
    contact_phone: str
    total_amount: float
    currency: str
    status: OrderStatus
    payment_method: PaymentMethod
    payment_reference: str | None
    photo_count: int
    created_at: datetime

    model_config = {"from_attributes": True}


class OrderConfirmRequest(BaseModel):
    approved: bool
