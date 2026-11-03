"""Parties d'un evenement (mairie, eglise, reception...).

Un seul evenement, un seul QR code, un seul pack et les memes prix : les parties
servent a ranger les photos et a les filtrer (onglets de la galerie). La
recherche par visage couvre toujours tout l'evenement.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.deps import require_verified_user
from app.models.event import Event
from app.models.event_section import EventSection
from app.models.photo import Photo
from app.models.user import User
from app.schemas.section import (
    PhotosSectionResult,
    PhotosSectionUpdate,
    SectionCreate,
    SectionRead,
    SectionUpdate,
)
from app.services.access import get_manageable_event
from app.services.face_clusters import face_cluster_cache
from app.services.sections import MAX_SECTIONS

router = APIRouter(prefix="/events", tags=["sections"])



async def list_sections(db: AsyncSession, event_id: uuid.UUID) -> list[SectionRead]:
    """Parties dans l'ordre d'affichage, avec leur nombre de photos."""
    counts = dict(
        (
            await db.execute(
                select(Photo.section_id, func.count(Photo.id))
                .where(Photo.event_id == event_id, Photo.section_id.is_not(None))
                .group_by(Photo.section_id)
            )
        ).all()
    )
    sections = (
        await db.execute(
            select(EventSection)
            .where(EventSection.event_id == event_id)
            .order_by(EventSection.position, EventSection.created_at)
        )
    ).scalars().all()
    return [
        SectionRead(
            id=s.id, name=s.name, starts_at=s.starts_at, location=s.location,
            position=s.position, photo_count=counts.get(s.id, 0),
        )
        for s in sections
    ]


async def get_event_section(db: AsyncSession, event_id: uuid.UUID, section_id: uuid.UUID) -> EventSection:
    section = await db.get(EventSection, section_id)
    if section is None or section.event_id != event_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Partie introuvable dans cet événement")
    return section


@router.get("/{event_id}/sections", response_model=list[SectionRead])
async def get_sections(event_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> list[SectionRead]:
    """Public : les onglets de la galerie (noms, dates, lieux)."""
    if await db.get(Event, event_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Événement introuvable")
    return await list_sections(db, event_id)


@router.post("/{event_id}/sections", response_model=SectionRead, status_code=status.HTTP_201_CREATED)
async def create_section(
    event_id: uuid.UUID,
    payload: SectionCreate,
    current_user: User = Depends(require_verified_user),
    db: AsyncSession = Depends(get_db),
) -> SectionRead:
    await get_manageable_event(event_id, current_user, db)
    existing = (
        await db.execute(select(func.count(EventSection.id)).where(EventSection.event_id == event_id))
    ).scalar_one()
    if existing >= MAX_SECTIONS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"{MAX_SECTIONS} parties au maximum par événement")
    section = EventSection(
        event_id=event_id, name=payload.name, starts_at=payload.starts_at,
        location=payload.location or None, position=existing,
    )
    db.add(section)
    await db.commit()
    return SectionRead(
        id=section.id, name=section.name, starts_at=section.starts_at,
        location=section.location, position=section.position, photo_count=0,
    )


@router.patch("/{event_id}/sections/{section_id}", response_model=list[SectionRead])
async def update_section(
    event_id: uuid.UUID,
    section_id: uuid.UUID,
    payload: SectionUpdate,
    current_user: User = Depends(require_verified_user),
    db: AsyncSession = Depends(get_db),
) -> list[SectionRead]:
    """Renvoie toutes les parties : changer la position deplace les autres."""
    await get_manageable_event(event_id, current_user, db)
    section = await get_event_section(db, event_id, section_id)
    data = payload.model_dump(exclude_unset=True)
    if "name" in data and data["name"]:
        section.name = data["name"]
    if "starts_at" in data:
        section.starts_at = data["starts_at"]
    if "location" in data:
        section.location = data["location"] or None
    if data.get("position") is not None:
        others = (
            await db.execute(
                select(EventSection)
                .where(EventSection.event_id == event_id, EventSection.id != section.id)
                .order_by(EventSection.position, EventSection.created_at)
            )
        ).scalars().all()
        ordered = list(others)
        ordered.insert(min(data["position"], len(ordered)), section)
        for i, s in enumerate(ordered):
            s.position = i
    await db.commit()
    return await list_sections(db, event_id)


@router.delete("/{event_id}/sections/{section_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_section(
    event_id: uuid.UUID,
    section_id: uuid.UUID,
    current_user: User = Depends(require_verified_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Supprime la partie, jamais ses photos : elles restent dans l'evenement, sans partie."""
    await get_manageable_event(event_id, current_user, db)
    section = await get_event_section(db, event_id, section_id)
    await db.execute(update(Photo).where(Photo.section_id == section.id).values(section_id=None))
    await db.delete(section)
    await db.commit()
    face_cluster_cache.invalidate(event_id)


@router.post("/{event_id}/photos/section", response_model=PhotosSectionResult)
async def move_photos_to_section(
    event_id: uuid.UUID,
    payload: PhotosSectionUpdate,
    current_user: User = Depends(require_verified_user),
    db: AsyncSession = Depends(get_db),
) -> PhotosSectionResult:
    """Range des photos de l'evenement dans une partie (selection de l'admin)."""
    await get_manageable_event(event_id, current_user, db)
    if payload.section_id is not None:
        await get_event_section(db, event_id, payload.section_id)
    result = await db.execute(
        update(Photo)
        .where(Photo.event_id == event_id, Photo.id.in_(payload.photo_ids))
        .values(section_id=payload.section_id)
    )
    await db.commit()
    # les groupes de visages gardent une copie des photos (avec leur partie)
    face_cluster_cache.invalidate(event_id)
    return PhotosSectionResult(moved=result.rowcount or 0)
