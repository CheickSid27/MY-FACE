import uuid
from datetime import datetime

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


class UserAdminRead(UserRead):
    """Vue admin d'un compte : activite et packs payes."""

    event_count: int = 0
    photo_count: int = 0
    packs_paid_total: int = 0
    packs_pending: int = 0


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
