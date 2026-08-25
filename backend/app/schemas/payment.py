import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.order import OrderStatus, PaymentMethod


class PaymentInitRequest(BaseModel):
    session_id: uuid.UUID
    contact_phone: str = Field(min_length=6, max_length=32)
    # Moyen de paiement choisi par le client (Wave, Orange Money...). Si
    # fourni, on utilise le flux QR + confirmation manuelle organisateur
    # (voir routers/payments.py). Si omis, on garde l'ancien comportement
    # (provider global PAYMENT_PROVIDER, utilise par le mode test "manual").
    payment_method: PaymentMethod | None = None


class PaymentInitResponse(BaseModel):
    order_id: uuid.UUID
    status: OrderStatus
    payment_method: PaymentMethod
    total_amount: float
    currency: str
    redirect_url: str | None = None
    instructions: str | None = None
    qr_image_url: str | None = None
    merchant_phone: str | None = None


class PaymentStatusResponse(BaseModel):
    order_id: uuid.UUID
    status: OrderStatus
    total_amount: float
    currency: str
    payment_method: PaymentMethod
    qr_image_url: str | None = None
    merchant_phone: str | None = None
