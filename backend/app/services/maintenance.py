"""Mode maintenance : un admin l'active d'un bouton (/admin/settings) et les
pages invites affichent « MYFACE revient dans quelques minutes » au lieu de
la galerie, du scan ou du panier. A l'activation, l'admin choisit si les
photographes sont aussi arretes (espace MYFACE Pro ferme, envois de photos et
achats de packs refuses) ; l'admin, lui, garde toujours l'acces.

Le serveur refuse aussi les nouvelles commandes des invites pendant la
maintenance : l'ecran des pages ne suffit pas (une page deja ouverte peut
encore envoyer une commande jusqu'a sa verification suivante). Les webhooks
de paiement et « j'ai paye » restent ouverts : l'argent deja parti doit
toujours etre enregistre.

Le reglage vit dans app_settings (cle « maintenance ») ; il est lu par chaque
page invite au chargement, donc garde en memoire quelques secondes pour ne pas
ajouter un aller-retour vers la base a chaque visite.
"""

import time
from datetime import datetime, timezone

from fastapi import HTTPException, status as http_status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.app_setting import AppSetting
from app.models.user import User, UserRole

SETTING_KEY = "maintenance"
DEFAULT_MESSAGE = "MYFACE est en maintenance. Revenez dans quelques minutes : vos photos vous attendent."
_CACHE_SECONDS = 5.0
_cache: tuple[float, dict] | None = None


def _normalize(value: dict | None) -> dict:
    value = value or {}
    message = (value.get("message") or "").strip() or None
    active = bool(value.get("active"))
    return {
        "active": active,
        "message": message,
        "since": value.get("since"),
        "photographers": active and bool(value.get("photographers")),
    }


async def get_status(db: AsyncSession) -> dict:
    global _cache
    now = time.monotonic()
    if _cache is not None and now - _cache[0] < _CACHE_SECONDS:
        return _cache[1]
    setting = await db.get(AppSetting, SETTING_KEY)
    status = _normalize(setting.value if setting else None)
    _cache = (now, status)
    return status


async def set_status(db: AsyncSession, active: bool, message: str | None, photographers: bool = False) -> dict:
    global _cache
    setting = await db.get(AppSetting, SETTING_KEY)
    previous = _normalize(setting.value if setting else None)
    # « depuis » ne bouge pas quand on corrige seulement le message
    since = previous["since"] if (active and previous["active"]) else (
        datetime.now(timezone.utc).isoformat() if active else None
    )
    value = _normalize({"active": active, "message": message, "since": since, "photographers": photographers})
    if setting is None:
        db.add(AppSetting(key=SETTING_KEY, value=value))
    else:
        setting.value = value
    await db.commit()
    _cache = None
    return value


def public_view(status: dict) -> dict:
    """Ce que voit un invite : pas de date interne, toujours un message."""
    return {
        "maintenance": status["active"],
        "message": (status["message"] or DEFAULT_MESSAGE) if status["active"] else None,
        "photographers": status["photographers"],
    }


def _closed(status: dict) -> HTTPException:
    return HTTPException(
        status_code=http_status.HTTP_503_SERVICE_UNAVAILABLE,
        detail=status["message"] or DEFAULT_MESSAGE,
        headers={"Retry-After": "60"},
    )


async def ensure_open_for_guests(db: AsyncSession) -> None:
    """Nouvelle commande d'un invite (ou de la borne) : refusee pendant la maintenance."""
    status = await get_status(db)
    if status["active"]:
        raise _closed(status)


async def ensure_open_for_user(db: AsyncSession, user: User) -> None:
    """Action d'un compte (envoi de photos, achat de pack) : l'admin passe
    toujours, le photographe seulement s'il n'est pas inclus dans la maintenance."""
    status = await get_status(db)
    if status["photographers"] and user.role != UserRole.ADMIN:
        raise _closed(status)


def reset_cache() -> None:
    global _cache
    _cache = None
