import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.pack_purchase import PackPurchaseStatus
from app.services.phone import normalize_phone, normalize_phone_or_ci

PackKey = Literal["decouverte", "evenement", "pro", "sur_mesure"]
PackPaymentMethod = Literal["wave", "orange", "mtn", "moov", "djamo"]


class PackRead(BaseModel):
    key: str
    name: str
    price: int | None
    photo_limit: int | None
    tagline: str
    highlights: list[str]
    features: list[str]
    purchasable: bool


class PackPurchaseCreate(BaseModel):
    pack: PackKey
    payment_method: PackPaymentMethod
    # Numero depuis lequel le photographe a paye (pour retrouver le transfert)
    payer_phone: str = Field(min_length=6, max_length=32)
    # Reference / ID de transaction affiche par Wave, Orange Money...
    transaction_ref: str = Field(min_length=3, max_length=80)

    @field_validator("payer_phone")
    @classmethod
    def _valid_phone(cls, value: str) -> str:
        return normalize_phone(value)

    @field_validator("transaction_ref")
    @classmethod
    def _strip_ref(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 3:
            raise ValueError("Référence de transaction trop courte")
        return value


class PaystackPurchaseCreate(BaseModel):
    pack: PackKey


class PaystackCheckout(BaseModel):
    purchase_id: uuid.UUID
    # Page Paystack ou le photographe choisit Wave, Orange Money, MTN ou carte
    authorization_url: str


class PackPurchaseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    event_id: uuid.UUID
    pack: str
    amount: int
    currency: str
    status: PackPurchaseStatus
    payment_method: str
    payer_phone: str | None
    transaction_ref: str | None
    admin_note: str | None
    created_at: datetime
    decided_at: datetime | None


class PackPurchaseAdminRead(PackPurchaseRead):
    event_name: str
    event_date: datetime
    current_pack: str
    photographer_email: str
    photographer_name: str | None
    photographer_phone: str | None


class PackUpgradeOption(BaseModel):
    key: str
    name: str
    price: int
    photo_limit: int | None
    amount_due: int


class EventPackRead(BaseModel):
    """Etat du pack d'un evenement, pour la page evenement du photographe."""

    event_id: uuid.UUID
    pack: PackRead
    # True pour les evenements d'un admin MYFACE : aucune limite
    unlimited: bool
    photo_limit: int | None
    photo_count: int
    remaining: int | None
    amount_paid: int
    features: list[str]
    upgrades: list[PackUpgradeOption]
    pending_purchase: PackPurchaseRead | None
    purchases: list[PackPurchaseRead]


class PackPaymentInfo(BaseModel):
    """Numeros Mobile Money de MYFACE ou les photographes paient leurs packs,
    et contact WhatsApp (pack sur mesure, questions)."""

    wave: str | None = None
    orange: str | None = None
    mtn: str | None = None
    moov: str | None = None
    djamo: str | None = None
    whatsapp: str | None = None
    instructions: str | None = Field(default=None, max_length=500)


class PackPaymentInfoUpdate(PackPaymentInfo):
    """Saisie de l'admin : chaque numero est verifie et mis au format
    international (un numero faux empecherait les photographes de payer).
    Sans indicatif, le numero est lu comme ivoirien."""

    @field_validator("wave", "orange", "mtn", "moov", "djamo", "whatsapp")
    @classmethod
    def _valid_phone(cls, value: str | None) -> str | None:
        if value is None or not value.strip():
            return None
        return normalize_phone_or_ci(value)


class AdminSetPackRequest(BaseModel):
    """Attribution directe d'un pack par un admin (offert, sur mesure)."""

    pack: PackKey
    photo_limit_override: int | None = Field(default=None, ge=1, le=100_000)
    note: str | None = Field(default=None, max_length=255)


class PackRejectRequest(BaseModel):
    note: str | None = Field(default=None, max_length=255)
