"""Parties d'un evenement : retrouver une partie par son nom (sous-dossier
« Mairie/ » du dossier surveille ou du dossier local du photographe), en la
creant si elle n'existe pas encore."""

import asyncio
import uuid
from collections import defaultdict

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.event_section import EventSection

MAX_SECTIONS = 20


def clean_section_name(name: str) -> str:
    return " ".join(name.split())[:120]


async def find_or_create_section(db: AsyncSession, event_id: uuid.UUID, name: str) -> EventSection | None:
    """Partie de ce nom (majuscules et espaces ignores), creee au besoin (sans
    date ni lieu). None si le nom est vide ou si l'evenement a deja 20 parties.
    N'enregistre pas : l'appelant fait le commit."""
    clean = clean_section_name(name)
    if not clean:
        return None
    existing = (
        await db.execute(
            select(EventSection).where(
                EventSection.event_id == event_id, func.lower(EventSection.name) == clean.lower()
            )
        )
    ).scalars().first()
    if existing is not None:
        return existing
    count = (await db.execute(select(func.count(EventSection.id)).where(EventSection.event_id == event_id))).scalar_one()
    if count >= MAX_SECTIONS:
        return None
    section = EventSection(event_id=event_id, name=clean, position=count)
    db.add(section)
    await db.flush()
    return section


def same_section(section_id: uuid.UUID | None):
    """Condition SQL « photo de cette partie » (None = photos sans partie)."""
    from app.models.photo import Photo

    return Photo.section_id.is_(None) if section_id is None else Photo.section_id == section_id


# Envois d'un meme evenement controles un par un (noms deja presents, place
# restante dans le pack) : deux envois simultanes du meme fichier (deux
# onglets qui synchronisent le meme dossier, vu le 03/11 : 970 copies)
# passaient tous les deux le controle avant l'enregistrement de l'autre.
_upload_locks: defaultdict[uuid.UUID, asyncio.Lock] = defaultdict(asyncio.Lock)


def event_upload_lock(event_id: uuid.UUID) -> asyncio.Lock:
    return _upload_locks[event_id]
