import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models.user import UserRole
from app.services.phone import normalize_phone


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
        return normalize_phone(value)


class UserAdminRead(UserRead):
    """Vue admin d'un compte : activite et packs payes."""

    event_count: int = 0
    photo_count: int = 0
    packs_paid_total: int = 0
    packs_pending: int = 0


class UserAdminUpdate(BaseModel):
    is_active: bool | None = None


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    role: UserRole = UserRole.PHOTOGRAPHE
