import uuid

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db
from app.core.security import InvalidTokenError, TokenType, decode_token_payload, issued_before
from app.models.user import User, UserRole

bearer_scheme = HTTPBearer()
optional_bearer_scheme = HTTPBearer(auto_error=False)

ACCOUNT_SUSPENDED_DETAIL = "Compte suspendu : contactez MYFACE sur WhatsApp"
SESSION_REVOKED_DETAIL = "Session expirée : reconnectez-vous"
EMAIL_NOT_VERIFIED_DETAIL = (
    "Confirmez d'abord votre adresse e-mail : cliquez sur le lien reçu par e-mail "
    "(pensez aux courriers indésirables)"
)


async def _user_from_access_token(token: str, db: AsyncSession) -> User:
    """Compte du jeton d'acces, ou InvalidTokenError (jeton invalide, compte
    introuvable, ou jeton emis avant le dernier changement de mot de passe)."""
    payload = decode_token_payload(token, TokenType.ACCESS)
    try:
        user_id = uuid.UUID(payload["sub"])
    except ValueError as exc:
        raise InvalidTokenError("Token invalide") from exc
    user = await db.get(User, user_id)
    if user is None:
        raise InvalidTokenError("Utilisateur introuvable")
    if issued_before(payload, user.password_changed_at):
        raise InvalidTokenError(SESSION_REVOKED_DETAIL)
    return user


async def get_optional_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(optional_bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User | None:
    """Utilisateur connecte s'il y en a un, sinon None (jamais d'erreur) :
    pour les routes accessibles soit a l'organisateur, soit a la borne."""
    if credentials is None:
        return None
    try:
        user = await _user_from_access_token(credentials.credentials, db)
    except InvalidTokenError:
        return None
    return user if user.is_active else None


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    try:
        user = await _user_from_access_token(credentials.credentials, db)
    except InvalidTokenError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=ACCOUNT_SUSPENDED_DETAIL)

    return user


async def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Réservé aux administrateurs")
    return current_user


async def require_verified_user(current_user: User = Depends(get_current_user)) -> User:
    """Photographe dont l'adresse e-mail est confirmee : obligatoire pour creer
    un evenement, envoyer des photos ou acheter un pack (un compte cree avec
    l'adresse de quelqu'un d'autre ne peut rien publier). Les admins ne sont
    pas concernes ; la regle ne s'applique que si l'envoi d'e-mails est en
    place (voir Settings.email_verification_enforced)."""
    if (
        current_user.role != UserRole.ADMIN
        and not current_user.email_verified
        and get_settings().email_verification_enforced
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=EMAIL_NOT_VERIFIED_DETAIL)
    return current_user
