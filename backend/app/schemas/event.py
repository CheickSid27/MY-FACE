import uuid
from datetime import datetime, timedelta
from typing import Annotated

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    computed_field,
    field_validator,
    model_validator,
)

from app.core.config import get_settings

# Plafonds de saisie : au-dela, c'est une faute de frappe (un zero de trop),
# pas un vrai tarif.
MAX_PRICE = 10_000_000
EVENT_YEAR_MIN = 2000
EVENT_YEAR_MAX = 2100


class PricingPack(BaseModel):
    """Lot a prix fixe : `count` photos pour `price` (ex: 10 photos pour 8000)."""

    count: int = Field(ge=2, le=1000)
    price: float = Field(gt=0, le=MAX_PRICE)


class PricingDiscount(BaseModel):
    """Remise de volume : `percent` % des `min_quantity` photos achetees."""

    min_quantity: int = Field(ge=2, le=10000)
    percent: float = Field(gt=0, lt=100)


class PricingConfig(BaseModel):
    # 0 accepte seulement quand les photos sont offertes (voir `offert`)
    unit_price: float = Field(ge=0, le=MAX_PRICE)
    currency: str = Field(default="XOF", pattern=r"^[A-Z]{3}$")
    packs: list[PricingPack] = Field(default_factory=list, max_length=20)
    discounts: list[PricingDiscount] = Field(default_factory=list, max_length=20)
    # Prix fixe par tirage papier (en plus du prix digital), choisi photo par
    # photo dans le panier. None/0 = impression non proposee pour cet
    # evenement. Pas de remise de volume dessus pour l'instant.
    print_unit_price: float | None = Field(default=None, ge=0, le=MAX_PRICE)
    # Prix « photo + tirage » a la borne : une photo achetee en numerique ET
    # imprimee coute ce prix tout compris (ex : 700 au lieu de 450 + 500).
    # Ces photos ne comptent pas dans les lots ni dans les remises. None/0 =
    # pas de prix combine (on retombe sur prix photo + print_unit_price).
    print_bundle_price: float | None = Field(default=None, ge=0, le=MAX_PRICE)
    # Photos offertes par l'organisateur : les invites telechargent sans
    # payer, il n'y a pas de page de paiement (voir POST /payments/offert).
    offert: bool = False

    @model_validator(mode="after")
    def _prix_si_payant(self) -> "PricingConfig":
        if not self.offert and self.unit_price <= 0:
            raise ValueError("Le prix par photo doit être supérieur à 0")
        return self

    @field_validator("packs")
    @classmethod
    def _unique_pack_sizes(cls, packs: list[PricingPack]) -> list[PricingPack]:
        if len({p.count for p in packs}) != len(packs):
            raise ValueError("Deux lots ne peuvent pas avoir le même nombre de photos")
        return packs

    @field_validator("discounts")
    @classmethod
    def _unique_discount_thresholds(cls, discounts: list[PricingDiscount]) -> list[PricingDiscount]:
        if len({d.min_quantity for d in discounts}) != len(discounts):
            raise ValueError("Deux remises ne peuvent pas avoir le même seuil")
        return discounts


def _check_event_date(value: datetime) -> datetime:
    if not EVENT_YEAR_MIN <= value.year <= EVENT_YEAR_MAX:
        raise ValueError("Date de l'événement invalide")
    return value


EventDate = Annotated[datetime, AfterValidator(_check_event_date)]


class EventCreate(BaseModel):
    # espaces en trop retires : un nom fait seulement d'espaces est refuse
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=255)
    date: EventDate
    location: str = Field(min_length=1, max_length=255)
    pricing: PricingConfig
    # Voir models/event.py : vide/absent = pas de cadre decoratif pour cet evenement.
    frame_caption: str | None = Field(default=None, max_length=255)


class EventUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str | None = Field(default=None, min_length=1, max_length=255)
    date: EventDate | None = None
    location: str | None = Field(default=None, min_length=1, max_length=255)
    pricing: PricingConfig | None = None
    frame_caption: str | None = Field(default=None, max_length=255)
    cash_enabled: bool | None = None
    # Packs Evenement et Pro (voir services/packs.py) : texte du filigrane des
    # apercus invites (vide = nom du studio) et mot de passe de la galerie
    # (chaine vide = retirer la protection).
    watermark_text: str | None = Field(default=None, max_length=40)
    gallery_password: str | None = Field(default=None, max_length=64)

    @field_validator("gallery_password")
    @classmethod
    def _password_length(cls, value: str | None) -> str | None:
        if value is not None and value.strip() and len(value.strip()) < 4:
            raise ValueError("Le mot de passe de la galerie doit faire au moins 4 caractères")
        return value


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
    pack: str = "decouverte"
    photo_limit_override: int | None = None
    watermark_text: str | None = None
    has_gallery_password: bool = False
    retention_exempt: bool = False
    photos_purged_at: datetime | None = None

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

    # Conservation des donnees (voir services/retention.py) : date de
    # suppression automatique des photos, None si l'evenement est exempte.
    @computed_field
    @property
    def photos_available_until(self) -> datetime | None:
        if self.retention_exempt:
            return None
        return self.date + timedelta(days=get_settings().retention_photo_days)


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
    # Paiement en ligne par Paystack propose (evenements de MYFACE)
    online_payment: bool = False
    # Service photographe : nom du studio affiche aux invites
    photographer_name: str | None = None
    # Photo de profil du photographe (GET /auth/avatars/{id}?v=...)
    photographer_id: uuid.UUID | None = None
    photographer_avatar_version: str | None = None
    # Galerie protegee par mot de passe, et acces deja accorde a ce visiteur
    # (jeton `access` valide, borne ou organisateur connecte).
    password_required: bool = False
    gallery_access: bool = True
    # Conservation des donnees : date jusqu'a laquelle les photos restent en
    # ligne (None = pas de suppression prevue), et photos deja supprimees.
    photos_available_until: datetime | None = None
    photos_purged: bool = False


class GalleryUnlockRequest(BaseModel):
    password: str = Field(min_length=1, max_length=64)


class GalleryUnlockResponse(BaseModel):
    access_token: str


class EventListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    date: datetime
    location: str
    photo_count: int = 0
    # Renseigne pour la vue admin (tous les evenements, tous organisateurs).
    organizer_email: str | None = None
    pack: str = "decouverte"
    # None = illimite (evenement d'un admin, ou sur mesure sans limite)
    photo_limit: int | None = None
    # Un achat de pack attend la validation de MYFACE
    pack_pending: bool = False


class EventIndexingSummary(BaseModel):
    pending: int
    processing: int
    done: int
    failed: int
    faces: int


class ReindexResponse(BaseModel):
    queued: int
