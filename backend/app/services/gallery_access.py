"""Galerie protegee par mot de passe (packs Evenement et Pro).

Quand l'organisateur fixe un mot de passe, les routes publiques qui montrent
des photos (galerie, « Trouver mon visage », recherche par selfie) exigent :
- soit le jeton d'acces obtenu en saisissant le mot de passe
  (POST /events/{id}/unlock), passe en parametre `access` ;
- soit le vrai kiosk_token (la borne, sur place) ;
- soit un utilisateur connecte qui gere l'evenement (organisateur, admin).

La page d'accueil de l'evenement (nom, date) reste publique : elle affiche
le champ du mot de passe."""

import hashlib

from fastapi import HTTPException, status

from app.core.security import (
    InvalidTokenError,
    TokenType,
    create_gallery_token,
    decode_token_payload,
)
from app.models.event import Event
from app.models.user import User
from app.services.access import can_manage_event, is_kiosk_request

GALLERY_ACCESS_HOURS = 24 * 7
PASSWORD_REQUIRED_DETAIL = "Mot de passe de la galerie requis"


def password_fingerprint(event: Event) -> str:
    return hashlib.sha256((event.gallery_password_hash or "").encode()).hexdigest()[:16]


def issue_gallery_token(event: Event) -> str:
    return create_gallery_token(str(event.id), password_fingerprint(event), GALLERY_ACCESS_HOURS)


def has_gallery_access(
    event: Event,
    *,
    kiosk_token: str | None = None,
    access_token: str | None = None,
    user: User | None = None,
) -> bool:
    if not event.gallery_password_hash:
        return True
    if is_kiosk_request(event, kiosk_token):
        return True
    if user is not None and can_manage_event(event, user):
        return True
    if access_token:
        try:
            payload = decode_token_payload(access_token, TokenType.GALLERY)
        except InvalidTokenError:
            return False
        return payload.get("sub") == str(event.id) and payload.get("pwd") == password_fingerprint(event)
    return False


def require_gallery_access(
    event: Event,
    *,
    kiosk_token: str | None = None,
    access_token: str | None = None,
    user: User | None = None,
) -> None:
    if not has_gallery_access(event, kiosk_token=kiosk_token, access_token=access_token, user=user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=PASSWORD_REQUIRED_DETAIL)
