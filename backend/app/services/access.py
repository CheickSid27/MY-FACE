"""Regles d'acces partagees entre routers.

- Un organisateur (role photographe) gere uniquement SES evenements.
- Un admin gere TOUS les evenements (vue globale, y compris ceux crees par
  un photographe) : auparavant il ne voyait que les siens, sans aucun moyen
  de superviser l'activite des comptes photographes qu'il cree.
- Le mode borne est accorde uniquement sur presentation du vrai kiosk_token
  de l'evenement, compare cote serveur."""

import secrets
import uuid

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.event import Event
from app.models.user import User, UserRole


def can_manage_event(event: Event, user: User) -> bool:
    return user.role == UserRole.ADMIN or event.organizer_id == user.id


async def get_manageable_event(event_id: uuid.UUID, user: User, db: AsyncSession) -> Event:
    event = await db.get(Event, event_id)
    if event is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evenement introuvable")
    if not can_manage_event(event, user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acces refuse")
    return event


def is_kiosk_request(event: Event, kiosk_token: str | None) -> bool:
    """True uniquement si `kiosk_token` est le vrai token de l'evenement
    (comparaison a temps constant : le token ne doit pas pouvoir etre devine
    caractere par caractere en mesurant les temps de reponse)."""
    return bool(kiosk_token) and secrets.compare_digest(kiosk_token, event.kiosk_token)
