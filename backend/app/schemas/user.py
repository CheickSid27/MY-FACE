import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, computed_field, field_validator

from app.core.config import get_settings
from app.models.user import UserRole
from app.schemas.auth import check_new_password
from app.services.phone import normalize_phone_or_ci


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    role: UserRole
    created_at: datetime
    display_name: str | None = None
    studio_name: str | None = None
    phone: str | None = None
    city: str | None = None
    is_active: bool = True
    email_verified: bool = False
    # Photo de profil : servie par GET /auth/avatars/{id}?v={avatar_version}
    avatar_version: str | None = None

    @computed_field
    @property
    def must_verify_email(self) -> bool:
        """Photographe bloque tant qu'il n'a pas confirme son adresse (seulement
        si l'envoi d'e-mails est en place) : le bandeau de son espace le dit."""
        return (
            self.role == UserRole.PHOTOGRAPHE
            and not self.email_verified
            and get_settings().email_verification_enforced
        )


class UserProfileUpdate(BaseModel):
    """Profil modifiable par le photographe lui-meme (page « Mon compte »)."""

    display_name: str | None = Field(default=None, min_length=2, max_length=120)
    studio_name: str | None = Field(default=None, max_length=120)
    phone: str | None = Field(default=None, max_length=32)
    city: str | None = Field(default=None, max_length=120)

    @field_validator("phone")
    @classmethod
    def _valid_phone(cls, value: str | None) -> str | None:
        if value is None or not value.strip():
            return None
        # sans indicatif, numero ivoirien (« 07 01 02 03 04 »)
        return normalize_phone_or_ci(value)


PayoutMethod = Literal["wave", "orange", "mtn", "bank"]


class PayoutRead(BaseModel):
    """Versement des ventes en ligne au photographe (partage Paystack)."""

    enabled: bool
    method: PayoutMethod | None = None
    account_masked: str | None = None
    name: str | None = None
    available: bool = True  # Paystack configure sur ce serveur


class PayoutUpdate(BaseModel):
    method: PayoutMethod
    # Numero Mobile Money (10 chiffres) ou RIB (24 caracteres)
    account: str = Field(min_length=8, max_length=40)
    name: str = Field(min_length=2, max_length=120)
    # Code banque Paystack (liste GET /payments/paystack/banks) si method == bank
    bank_code: str | None = Field(default=None, max_length=20)


class AdminPayoutCode(BaseModel):
    """Sous-compte cree a la main dans le tableau de bord Paystack."""

    subaccount_code: str = Field(pattern=r"^ACCT_[A-Za-z0-9]+$", max_length=40)


class UserAdminRead(UserRead):
    """Vue admin d'un compte : activite et packs payes."""

    event_count: int = 0
    photo_count: int = 0
    packs_paid_total: int = 0
    packs_pending: int = 0
    payout_enabled: bool = False
    paystack_subaccount_code: str | None = None


class UserAdminUpdate(BaseModel):
    is_active: bool | None = None
    # Confirmation manuelle de l'adresse (photographe qui ne recoit pas l'e-mail)
    email_verified: bool | None = None


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    role: UserRole = UserRole.PHOTOGRAPHE

    @field_validator("email")
    @classmethod
    def _lower_email(cls, value: str) -> str:
        return value.lower()

    @field_validator("password")
    @classmethod
    def _strong_password(cls, value: str) -> str:
        return check_new_password(value)
