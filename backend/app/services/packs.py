"""Packs du service photographe : memes tarifs que Fokevani (relevés le
21/10/2026 sur fokevani.com/tarifs), paiement unique par evenement, sans
abonnement.

- Decouverte : gratuit, 10 photos par evenement ;
- Evenement : 10 000 FCFA, 500 photos, mot de passe de galerie, filigrane
  au nom du photographe ;
- Pro : 25 000 FCFA, 2 000 photos, + assistance prioritaire le jour J ;
- Sur mesure : sur devis (studios, agences), attribue par un admin.

Les evenements d'un admin MYFACE (nos propres evenements, avec borne et
equipe sur place) ne sont jamais limites.
"""

import uuid
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.event import Event
from app.models.pack_purchase import PackPurchase, PackPurchaseStatus
from app.models.photo import Photo
from app.models.user import User, UserRole
from app.services.watermark import WATERMARK_TEXT

FEATURE_GALLERY_PASSWORD = "gallery_password"
FEATURE_CUSTOM_WATERMARK = "custom_watermark"
FEATURE_PRIORITY_SUPPORT = "priority_support"
ALL_FEATURES = frozenset({FEATURE_GALLERY_PASSWORD, FEATURE_CUSTOM_WATERMARK, FEATURE_PRIORITY_SUPPORT})

DEFAULT_PACK = "decouverte"
UNLIMITED_PACK = "sur_mesure"


@dataclass(frozen=True)
class Pack:
    key: str
    name: str
    # None = sur devis
    price: int | None
    # None = pas de limite (sur mesure sans limite negociee)
    photo_limit: int | None
    tagline: str
    highlights: tuple[str, ...]
    features: frozenset[str]
    # Achetable en ligne par le photographe (le sur mesure passe par un admin)
    purchasable: bool


PACKS: dict[str, Pack] = {
    "decouverte": Pack(
        key="decouverte",
        name="Découverte",
        price=0,
        photo_limit=10,
        tagline="Pour essayer MYFACE sur un petit événement",
        highlights=(
            "10 photos par événement",
            "IA de reconnaissance faciale",
            "QR code et page invités",
            "Galerie, « Trouver mon visage » et selfie",
            "Vente aux invités ou photos offertes",
            "Photos en ligne 90 jours après l'événement",
        ),
        features=frozenset(),
        purchasable=False,
    ),
    "evenement": Pack(
        key="evenement",
        name="Événement",
        price=10_000,
        photo_limit=500,
        tagline="Mariages, anniversaires, conférences",
        highlights=(
            "500 photos par événement",
            "Tout le pack Découverte",
            "Mot de passe de galerie",
            "Filigrane à votre nom",
        ),
        features=frozenset({FEATURE_GALLERY_PASSWORD, FEATURE_CUSTOM_WATERMARK}),
        purchasable=True,
    ),
    "pro": Pack(
        key="pro",
        name="Pro",
        price=25_000,
        photo_limit=2_000,
        tagline="Photographes et grands événements",
        highlights=(
            "2 000 photos par événement",
            "Tout le pack Événement",
            "Assistance prioritaire le jour J",
        ),
        features=ALL_FEATURES,
        purchasable=True,
    ),
    "sur_mesure": Pack(
        key="sur_mesure",
        name="Sur mesure",
        price=None,
        photo_limit=None,
        tagline="Studios, agences et organisateurs réguliers",
        highlights=(
            "Carnet d'événements prépayés à prix réduit",
            "Limite de photos adaptée",
            "Assistance le jour J",
            "Facture au nom de votre entreprise",
        ),
        features=ALL_FEATURES,
        purchasable=False,
    ),
}
PACK_ORDER = ("decouverte", "evenement", "pro", "sur_mesure")


def get_pack(key: str | None) -> Pack:
    return PACKS.get(key or DEFAULT_PACK, PACKS[DEFAULT_PACK])


def pack_rank(key: str | None) -> int:
    return PACK_ORDER.index(get_pack(key).key)


def is_unlimited_owner(owner: User | None) -> bool:
    return owner is not None and owner.role == UserRole.ADMIN


def effective_photo_limit(event: Event, owner: User | None) -> int | None:
    """Nombre maximum de photos de l'evenement, None = illimite."""
    if is_unlimited_owner(owner):
        return None
    if event.photo_limit_override:
        return event.photo_limit_override
    return get_pack(event.pack).photo_limit


def event_has_feature(event: Event, owner: User | None, feature: str) -> bool:
    if is_unlimited_owner(owner):
        return True
    return feature in get_pack(event.pack).features


def next_pack(key: str | None) -> Pack | None:
    """Premier pack achetable au-dessus du pack actuel (pour les messages)."""
    rank = pack_rank(key)
    for candidate in PACK_ORDER[rank + 1:]:
        if PACKS[candidate].purchasable:
            return PACKS[candidate]
    return None


def limit_reached_message(event: Event, limit: int) -> str:
    pack = get_pack(event.pack)
    message = f"Limite du pack {pack.name} atteinte ({limit} photos)"
    upgrade = next_pack(event.pack)
    if upgrade is not None and upgrade.photo_limit:
        message += f" : passez au pack {upgrade.name} ({upgrade.photo_limit} photos) pour en ajouter"
    return message


def amount_due(target_key: str, already_paid: int) -> int:
    price = get_pack(target_key).price or 0
    return max(0, price - already_paid)


def watermark_text_for(event: Event, owner: User | None) -> str:
    """Texte du filigrane des apercus invites : personnalisable a partir du
    pack Evenement (texte choisi, sinon nom du studio), MYFACE sinon."""
    if event_has_feature(event, owner, FEATURE_CUSTOM_WATERMARK):
        custom = (event.watermark_text or "").strip()
        if custom:
            return custom
        if owner is not None and owner.role == UserRole.PHOTOGRAPHE and owner.public_name:
            return owner.public_name
    return WATERMARK_TEXT


async def get_owner(db: AsyncSession, event: Event) -> User | None:
    return await db.get(User, event.organizer_id)


async def count_event_photos(db: AsyncSession, event_id: uuid.UUID) -> int:
    result = await db.execute(select(func.count(Photo.id)).where(Photo.event_id == event_id))
    return int(result.scalar_one())


async def amount_paid_for_event(db: AsyncSession, event_id: uuid.UUID) -> int:
    result = await db.execute(
        select(func.coalesce(func.sum(PackPurchase.amount), 0)).where(
            PackPurchase.event_id == event_id, PackPurchase.status == PackPurchaseStatus.PAID
        )
    )
    return int(result.scalar_one())


async def remaining_photo_slots(db: AsyncSession, event: Event, owner: User | None) -> int | None:
    """Photos encore autorisees, None = illimite."""
    limit = effective_photo_limit(event, owner)
    if limit is None:
        return None
    return max(0, limit - await count_event_photos(db, event.id))
