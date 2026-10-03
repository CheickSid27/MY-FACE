import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.photo import PhotoRead


class CartAddRequest(BaseModel):
    session_id: uuid.UUID | None = None
    event_id: uuid.UUID
    photo_id: uuid.UUID


class CartAddBulkRequest(BaseModel):
    session_id: uuid.UUID | None = None
    event_id: uuid.UUID
    # Une seule requete pour ajouter plusieurs photos (selection rapide de
    # plusieurs photos, "tout selectionner" sur un cluster de visages...) au
    # lieu d'un aller-retour reseau par photo : evite a la fois la lenteur
    # perceptible (chaque aller-retour paie la latence vers la base distante)
    # et le risque d'incoherence si le client navigue avant que toutes les
    # requetes individuelles n'aient fini.
    photo_ids: list[uuid.UUID] = Field(min_length=1, max_length=500)


class CartItemRead(BaseModel):
    id: uuid.UUID
    photo: PhotoRead
    print_requested: bool = False


class PricingBreakdownRead(BaseModel):
    photo_count: int
    subtotal: float
    discount_percent: float
    discount_amount: float
    print_count: int
    print_total: float
    total: float
    currency: str
    bundle: bool = False


class CartRead(BaseModel):
    session_id: uuid.UUID
    event_id: uuid.UUID
    items: list[CartItemRead]
    pricing: PricingBreakdownRead
    expires_at: datetime


class CartItemUpdateRequest(BaseModel):
    print_requested: bool
    # Jeton de la borne : obligatoire pour COCHER un tirage papier (une
    # imprimante n'existe que sur place, jamais sur le telephone d'un invite).
    kiosk_token: str | None = None
