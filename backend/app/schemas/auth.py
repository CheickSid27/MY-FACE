import re

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.services.phone import normalize_phone

PASSWORD_MIN_LENGTH = 8
PASSWORD_MAX_LENGTH = 128


def check_new_password(value: str) -> str:
    """Regle commune a l'inscription, au changement et a la reinitialisation
    du mot de passe : 8 caracteres minimum, dont au moins une lettre et un
    chiffre (« 12345678 » ou « motdepasse » sont refuses)."""
    if not value.strip():
        raise ValueError("Le mot de passe ne peut pas être vide")
    if not re.search(r"[A-Za-zÀ-ÿ]", value) or not re.search(r"\d", value):
        raise ValueError("Le mot de passe doit contenir au moins une lettre et un chiffre")
    return value


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=PASSWORD_MAX_LENGTH)


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
    current_password: str = Field(min_length=1, max_length=PASSWORD_MAX_LENGTH)
    new_password: str = Field(min_length=PASSWORD_MIN_LENGTH, max_length=PASSWORD_MAX_LENGTH)

    @field_validator("new_password")
    @classmethod
    def _strong_password(cls, value: str) -> str:
        return check_new_password(value)


class RegisterRequest(BaseModel):
    """Inscription libre d'un photographe (service photographe) : le compte
    demarre au pack Decouverte (gratuit) sur chacun de ses evenements."""

    email: EmailStr
    password: str = Field(min_length=PASSWORD_MIN_LENGTH, max_length=PASSWORD_MAX_LENGTH)
    display_name: str = Field(min_length=2, max_length=120)
    studio_name: str | None = Field(default=None, max_length=120)
    # Numero WhatsApp / Mobile Money, au format international (E.164)
    phone: str = Field(min_length=6, max_length=32)
    city: str | None = Field(default=None, max_length=120)
    accept_terms: bool

    @field_validator("password")
    @classmethod
    def _strong_password(cls, value: str) -> str:
        return check_new_password(value)

    @field_validator("display_name")
    @classmethod
    def _real_name(cls, value: str) -> str:
        value = " ".join(value.split())
        if len(value) < 2:
            raise ValueError("Indiquez votre nom et prénom")
        return value

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


class VerifyEmailRequest(BaseModel):
    token: str = Field(min_length=10, max_length=2048)


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str = Field(min_length=10, max_length=2048)
    new_password: str = Field(min_length=PASSWORD_MIN_LENGTH, max_length=PASSWORD_MAX_LENGTH)

    @field_validator("new_password")
    @classmethod
    def _strong_password(cls, value: str) -> str:
        return check_new_password(value)
