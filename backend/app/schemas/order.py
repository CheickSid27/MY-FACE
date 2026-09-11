import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.order import OrderStatus, PaymentMethod
from app.schemas.photo import PhotoRead


class OrderRead(BaseModel):
    id: uuid.UUID
    contact_phone: str
    total_amount: float
    currency: str
    status: OrderStatus
    payment_method: PaymentMethod
    payment_reference: str | None
    photo_count: int
    print_count: int = 0
    # Date d'impression des tirages papier (None = a imprimer, s'il y en a).
    printed_at: datetime | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class OrderItemRead(BaseModel):
    photo: PhotoRead
    unit_price: float
    print_requested: bool
    print_price: float | None


class OrderDetailRead(OrderRead):
    """Fiche d'une commande pour l'organisateur, utilisable comme recu quand
    un client revient avec un probleme : liste nominative des photos
    achetees, tirages demandes, detail du prix, lien de telechargement."""

    event_id: uuid.UUID
    event_name: str
    event_date: datetime
    updated_at: datetime
    items: list[OrderItemRead]
    # Detail du montant (prix figes au moment de l'achat) : photos au prix
    # unitaire + tirages papier - lots/remises appliques = total paye.
    photos_subtotal: float
    prints_total: float
    discount_amount: float
    # Page de telechargement du client (permanente une fois la commande payee).
    download_url: str


class OrderConfirmRequest(BaseModel):
    approved: bool
