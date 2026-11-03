from pydantic import BaseModel, Field


class PhoneCountryRead(BaseModel):
    iso: str
    name: str
    dial_code: str
    # Expression reguliere du numero national (sans indicatif), identique a
    # la validation serveur (services/phone.py).
    pattern: str
    example: str
    hint: str
    trunk_prefix: str | None = None


class MaintenanceStatusRead(BaseModel):
    """Ce que voient les pages invites (public)."""

    maintenance: bool
    message: str | None = None
    photographers: bool = False


class MaintenanceAdminRead(BaseModel):
    active: bool
    message: str | None = None
    since: str | None = None
    photographers: bool = False


class MaintenanceUpdate(BaseModel):
    active: bool
    message: str | None = Field(default=None, max_length=300)
    # aussi fermer l'espace des photographes (l'admin garde l'acces)
    photographers: bool = False
