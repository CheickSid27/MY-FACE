import uuid

from pydantic import BaseModel, Field, field_validator

from app.models.order import OrderStatus, PaymentMethod
from app.services.phone import normalize_phone


class PaymentInitRequest(BaseModel):
    session_id: uuid.UUID
    # Numero international ("+2250701020304"), valide selon le format reel
    # du pays et stocke en E.164 (voir services/phone.py).
    contact_phone: str = Field(min_length=6, max_length=32)
    # Moyen de paiement choisi par le client : QR marchand configure par
    # l'organisateur (Wave, Orange Money...) ou especes (borne). Obligatoire :
    # l'ancien repli sans moyen de paiement creait des commandes que
    # personne ne pouvait ni payer ni confirmer (voir services/payments.py).
    payment_method: PaymentMethod
    # Jeton de la borne : obligatoire pour payer en especes (quelqu'un doit
    # physiquement recevoir l'argent : jamais depuis le telephone d'un invite).
    kiosk_token: str | None = None

    @field_validator("contact_phone")
    @classmethod
    def _valid_phone(cls, value: str) -> str:
        return normalize_phone(value)


class FreeOrderRequest(BaseModel):
    """Photos offertes : pas de moyen de paiement, juste le panier et le
    numero du client (garde avec la commande)."""

    session_id: uuid.UUID
    contact_phone: str = Field(min_length=6, max_length=32)
    kiosk_token: str | None = None

    @field_validator("contact_phone")
    @classmethod
    def _valid_phone(cls, value: str) -> str:
        return normalize_phone(value)


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
