import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class PricingConfig(BaseModel):
    unit_price: float = Field(gt=0)
    currency: str = "XOF"
    packs: list[dict] = Field(default_factory=list)
    discounts: list[dict] = Field(default_factory=list)
    # Prix fixe par tirage papier (en plus du prix digital), choisi photo par
    # photo dans le panier. None/0 = impression non proposee pour cet
    # evenement. Pas de remise de volume dessus pour l'instant.
    print_unit_price: float | None = Field(default=None, ge=0)


class EventCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    date: datetime
    location: str = Field(min_length=1, max_length=255)
    pricing: PricingConfig
    # Voir models/event.py : vide/absent = pas de cadre decoratif pour cet evenement.
    frame_caption: str | None = Field(default=None, max_length=255)


class EventUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    date: datetime | None = None
    location: str | None = Field(default=None, min_length=1, max_length=255)
    pricing: PricingConfig | None = None
    frame_caption: str | None = Field(default=None, max_length=255)
    cash_enabled: bool | None = None


class EventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    date: datetime
    location: str
    kiosk_token: str
    pricing: dict
    frame_caption: str | None
    cash_enabled: bool
    organizer_id: uuid.UUID
    created_at: datetime
    updated_at: datetime


class EventPublicRead(BaseModel):
    """Vue publique (invite/borne) : pas de kiosk_token ni organizer_id.
    `is_kiosk` est calcule cote serveur a partir d'un `kiosk_token` fourni en
    query param (voir routers/events.py, get_event_public) — jamais le vrai
    token n'est renvoye dans cette reponse, seulement ce booleen, pour qu'un
    client ne puisse pas le deviner en inspectant le reseau."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    date: datetime
    location: str
    pricing: dict
    frame_caption: str | None
    cash_enabled: bool
    is_kiosk: bool = False


class EventListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    date: datetime
    location: str
    photo_count: int = 0
