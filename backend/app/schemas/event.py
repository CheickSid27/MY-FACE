import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class PricingConfig(BaseModel):
    unit_price: float = Field(gt=0)
    currency: str = "XOF"
    packs: list[dict] = Field(default_factory=list)
    discounts: list[dict] = Field(default_factory=list)


class EventCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    date: datetime
    location: str = Field(min_length=1, max_length=255)
    pricing: PricingConfig


class EventUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    date: datetime | None = None
    location: str | None = Field(default=None, min_length=1, max_length=255)
    pricing: PricingConfig | None = None


class EventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    date: datetime
    location: str
    kiosk_token: str
    pricing: dict
    organizer_id: uuid.UUID
    created_at: datetime
    updated_at: datetime


class EventPublicRead(BaseModel):
    """Vue publique (invite/borne) : pas de kiosk_token ni organizer_id."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    date: datetime
    location: str
    pricing: dict


class EventListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    date: datetime
    location: str
    photo_count: int = 0
