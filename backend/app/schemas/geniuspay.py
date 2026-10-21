import uuid

from pydantic import BaseModel, Field, field_validator

from app.services.phone import normalize_phone


class GeniusPayInitRequest(BaseModel):
    session_id: uuid.UUID
    contact_phone: str = Field(min_length=6, max_length=32)

    @field_validator("contact_phone")
    @classmethod
    def _valid_phone(cls, value: str) -> str:
        return normalize_phone(value)


class GeniusPayInitResponse(BaseModel):
    order_id: uuid.UUID
    checkout_url: str
    status: str
    environment: str
