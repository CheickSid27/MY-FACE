import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any

import bcrypt
import jwt

from app.core.config import get_settings

settings = get_settings()

# bcrypt tronque en interne au-dela de 72 bytes ; on l'impose explicitement
# pour eviter un comportement silencieusement incoherent sur mots de passe longs.
_BCRYPT_MAX_BYTES = 72


class TokenType(str, Enum):
    ACCESS = "access"
    REFRESH = "refresh"
    # Acces invite a une galerie protegee par mot de passe (voir
    # services/gallery_access.py) : sujet = id de l'evenement.
    GALLERY = "gallery"
    # Liens envoyes par e-mail (voir routers/auth.py) : sujet = id du compte.
    EMAIL_VERIFY = "email_verify"
    PASSWORD_RESET = "password_reset"


def hash_password(password: str) -> str:
    password_bytes = password.encode("utf-8")[:_BCRYPT_MAX_BYTES]
    return bcrypt.hashpw(password_bytes, bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    password_bytes = plain_password.encode("utf-8")[:_BCRYPT_MAX_BYTES]
    return bcrypt.checkpw(password_bytes, hashed_password.encode("utf-8"))


# Hash d'un mot de passe que personne ne connait : la connexion avec un e-mail
# inconnu fait le meme calcul bcrypt qu'avec un vrai compte, pour que le temps
# de reponse ne revele pas quelles adresses ont un compte.
_DUMMY_HASH = hash_password(secrets.token_urlsafe(16))


def burn_password_check(plain_password: str) -> None:
    verify_password(plain_password, _DUMMY_HASH)


def secret_fingerprint(value: str) -> str:
    """Empreinte courte d'une valeur secrete (hash du mot de passe), placee
    dans un jeton pour l'invalider des que la valeur change."""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]


def _create_token(
    subject: str, token_type: TokenType, expires_delta: timedelta, extra: dict[str, Any] | None = None
) -> str:
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": subject,
        "type": token_type.value,
        "iat": now,
        "exp": now + expires_delta,
        **(extra or {}),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def create_access_token(subject: str) -> str:
    return _create_token(
        subject,
        TokenType.ACCESS,
        timedelta(minutes=settings.jwt_access_token_expire_minutes),
    )


def create_refresh_token(subject: str) -> str:
    return _create_token(
        subject,
        TokenType.REFRESH,
        timedelta(days=settings.jwt_refresh_token_expire_days),
    )


def create_gallery_token(event_id: str, password_fingerprint: str, hours: int) -> str:
    """`password_fingerprint` change avec le mot de passe : changer le mot de
    passe de la galerie invalide les acces deja donnes."""
    return _create_token(event_id, TokenType.GALLERY, timedelta(hours=hours), {"pwd": password_fingerprint})


def create_email_verification_token(user_id: str, email: str) -> str:
    """Lien de confirmation : lie a l'adresse, il ne vaut plus si elle change."""
    return _create_token(
        user_id,
        TokenType.EMAIL_VERIFY,
        timedelta(minutes=settings.unverified_account_ttl_minutes),
        {"email": email.lower()},
    )


def create_password_reset_token(user_id: str, hashed_password: str) -> str:
    """Lien de reinitialisation : lie au mot de passe actuel, il ne sert donc
    qu'une fois (le nouveau mot de passe change l'empreinte)."""
    return _create_token(
        user_id,
        TokenType.PASSWORD_RESET,
        timedelta(minutes=settings.password_reset_ttl_minutes),
        {"pwd": secret_fingerprint(hashed_password)},
    )


def issued_before(payload: dict[str, Any], moment: datetime | None) -> bool:
    """True si le jeton a ete emis avant `moment` (ex : dernier changement
    de mot de passe). `iat` est en secondes entieres : on compare a la
    seconde pres, sans quoi un jeton cree dans la meme seconde serait refuse."""
    if moment is None:
        return False
    issued_at = payload.get("iat")
    if not isinstance(issued_at, (int, float)):
        return True
    return int(issued_at) < int(moment.timestamp())


class InvalidTokenError(Exception):
    pass


def decode_token_payload(token: str, expected_type: TokenType) -> dict[str, Any]:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])
    except jwt.PyJWTError as exc:
        raise InvalidTokenError("Token invalide ou expire") from exc
    if payload.get("type") != expected_type.value:
        raise InvalidTokenError(f"Type de token invalide, attendu '{expected_type.value}'")
    if not payload.get("sub"):
        raise InvalidTokenError("Token sans sujet")
    return payload


def decode_token(token: str, expected_type: TokenType) -> str:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])
    except jwt.PyJWTError as exc:
        raise InvalidTokenError("Token invalide ou expire") from exc

    if payload.get("type") != expected_type.value:
        raise InvalidTokenError(f"Type de token invalide, attendu '{expected_type.value}'")

    subject = payload.get("sub")
    if not subject:
        raise InvalidTokenError("Token sans sujet")

    return subject
