import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator

from app.core.config import get_settings


class PricingPack(BaseModel):
    """Lot a prix fixe : `count` photos pour `price` (ex: 10 photos pour 8000)."""

    count: int = Field(ge=2, le=1000)
    price: float = Field(gt=0)


class PricingDiscount(BaseModel):
    """Remise de volume : `percent` % des `min_quantity` photos achetees."""

    min_quantity: int = Field(ge=2, le=10000)
    percent: float = Field(gt=0, lt=100)


class PricingConfig(BaseModel):
    unit_price: float = Field(gt=0)
    currency: str = "XOF"
    packs: list[PricingPack] = Field(default_factory=list, max_length=20)
    discounts: list[PricingDiscount] = Field(default_factory=list, max_length=20)
    # Prix fixe par tirage papier (en plus du prix digital), choisi photo par
    # photo dans le panier. None/0 = impression non proposee pour cet
    # evenement. Pas de remise de volume dessus pour l'instant.
    print_unit_price: float | None = Field(default=None, ge=0)
    # Prix « photo + tirage » a la borne : une photo achetee en numerique ET
    # imprimee coute ce prix tout compris (ex : 700 au lieu de 450 + 500).
    # Ces photos ne comptent pas dans les lots ni dans les remises. None/0 =
    # pas de prix combine (on retombe sur prix photo + print_unit_price).
    print_bundle_price: float | None = Field(default=None, ge=0)

    @field_validator("packs")
    @classmethod
    def _unique_pack_sizes(cls, packs: list[PricingPack]) -> list[PricingPack]:
        if len({p.count for p in packs}) != len(packs):
            raise ValueError("Deux lots ne peuvent pas avoir le meme nombre de photos")
        return packs

    @field_validator("discounts")
    @classmethod
    def _unique_discount_thresholds(cls, discounts: list[PricingDiscount]) -> list[PricingDiscount]:
        if len({d.min_quantity for d in discounts}) != len(discounts):
            raise ValueError("Deux remises ne peuvent pas avoir le meme seuil")
        return discounts


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

    # Liens a partager, construits sur l'URL publique de l'app (APP_BASE_URL,
    # la meme que celle des SMS et du QR de telechargement) : lien invite a
    # diffuser (QR imprime sur place, message...) et lien borne a ouvrir
    # uniquement sur l'appareil physique.
    @computed_field
    @property
    def guest_url(self) -> str:
        return f"{get_settings().app_base_url}/event/{self.id}"

    @computed_field
    @property
    def kiosk_url(self) -> str:
        return f"{get_settings().app_base_url}/event/{self.id}?kiosk={self.kiosk_token}"


class EventPublicRead(BaseModel):
    """Vue publique (invite/borne) : pas de kiosk_token ni organizer_id.
    `is_kiosk` est calcule cote serveur a partir d'un `kiosk_token` fourni en
    query param (voir routers/events.py, get_event_public), jamais le vrai
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
    # Renseigne pour la vue admin (tous les evenements, tous organisateurs).
    organizer_email: str | None = None


class EventIndexingSummary(BaseModel):
    pending: int
    processing: int
    done: int
    failed: int
    faces: int


class ReindexResponse(BaseModel):
    queued: int
