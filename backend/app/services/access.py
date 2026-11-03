"""Regles d'acces partagees entre routers.

- Un organisateur (role photographe) gere uniquement SES evenements.
- Un admin gere ses evenements, et ceux d'un photographe SEULEMENT si le
  photographe l'y a autorise (bouton « Autoriser MYFACE », jusqu'a ce qu'il le
  retire). Sinon l'admin ne voit que le resume (liste des evenements) et la
  galerie invite : chacun son espace (demande du 03/11, apres des doublons
  crees par la page de gestion ouverte en meme temps cote admin et cote
  photographe).
- Le mode borne est accorde uniquement sur presentation du vrai kiosk_token
  de l'evenement, compare cote serveur."""

import secrets
import uuid

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.event import Event
from app.models.user import User, UserRole


def can_manage_event(event: Event, user: User) -> bool:
    return event.organizer_id == user.id or (user.role == UserRole.ADMIN and event.admin_access)


def can_view_gallery(event: Event, user: User) -> bool:
    """Galerie invite (sans mot de passe) : l'organisateur, l'admin autorise,
    et l'equipe MYFACE en lecture."""
    return user.role == UserRole.ADMIN or can_manage_event(event, user)


async def get_manageable_event(event_id: uuid.UUID, user: User, db: AsyncSession) -> Event:
    event = await db.get(Event, event_id)
    if event is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Événement introuvable")
    if not can_manage_event(event, user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accès refusé")
    return event


def is_kiosk_request(event: Event, kiosk_token: str | None) -> bool:
    """True uniquement si `kiosk_token` est le vrai token de l'evenement
    (comparaison a temps constant : le token ne doit pas pouvoir etre devine
    caractere par caractere en mesurant les temps de reponse)."""
    return bool(kiosk_token) and secrets.compare_digest(kiosk_token, event.kiosk_token)
