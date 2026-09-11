from pydantic import BaseModel


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
