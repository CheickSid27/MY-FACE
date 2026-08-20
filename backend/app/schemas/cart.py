import uuid
from datetime import datetime

from pydantic import BaseModel

from app.schemas.photo import PhotoRead


class CartAddRequest(BaseModel):
    session_id: uuid.UUID | None = None
    event_id: uuid.UUID
    photo_id: uuid.UUID


class CartItemRead(BaseModel):
    id: uuid.UUID
    photo: PhotoRead


class PricingBreakdownRead(BaseModel):
    photo_count: int
    subtotal: float
    discount_percent: float
    discount_amount: float
    total: float
    currency: str


class CartRead(BaseModel):
    session_id: uuid.UUID
    event_id: uuid.UUID
    items: list[CartItemRead]
    pricing: PricingBreakdownRead
    expires_at: datetime
