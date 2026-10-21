from pydantic import BaseModel, EmailStr, Field, field_validator

from app.services.phone import normalize_phone


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class AccessTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class PasswordChangeRequest(BaseModel):
    current_password: str = Field(min_length=1)
    new_password: str = Field(min_length=8)


class RegisterRequest(BaseModel):
    """Inscription libre d'un photographe (service photographe) : le compte
    demarre au pack Decouverte (gratuit) sur chacun de ses evenements."""

    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    display_name: str = Field(min_length=2, max_length=120)
    studio_name: str | None = Field(default=None, max_length=120)
    # Numero WhatsApp / Mobile Money, au format international (E.164)
    phone: str = Field(min_length=6, max_length=32)
    city: str | None = Field(default=None, max_length=120)
    accept_terms: bool

    @field_validator("phone")
    @classmethod
    def _valid_phone(cls, value: str) -> str:
        return normalize_phone(value)

    @field_validator("accept_terms")
    @classmethod
    def _terms_required(cls, value: bool) -> bool:
        if not value:
            raise ValueError("Vous devez accepter les conditions d'utilisation")
        return value
