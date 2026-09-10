import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import (
    InvalidTokenError,
    TokenType,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.deps import get_current_user
from app.models.user import User
from app.schemas.auth import (
    AccessTokenResponse,
    LoginRequest,
    PasswordChangeRequest,
    RefreshRequest,
    TokenResponse,
)
from app.schemas.user import UserRead

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    result = await db.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()

    if user is None or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Email ou mot de passe incorrect")

    subject = str(user.id)
    return TokenResponse(
        access_token=create_access_token(subject),
        refresh_token=create_refresh_token(subject),
    )


@router.post("/refresh", response_model=AccessTokenResponse)
async def refresh(payload: RefreshRequest, db: AsyncSession = Depends(get_db)) -> AccessTokenResponse:
    try:
        subject = decode_token(payload.refresh_token, TokenType.REFRESH)
    except InvalidTokenError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

    try:
        user_id = uuid.UUID(subject)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token invalide") from exc

    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Utilisateur introuvable")

    return AccessTokenResponse(access_token=create_access_token(subject))


@router.get("/me", response_model=UserRead)
async def me(current_user: User = Depends(get_current_user)) -> User:
    return current_user


@router.post("/password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(
    payload: PasswordChangeRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Permet a un utilisateur deja authentifie de changer son propre mot de
    passe — notamment le mot de passe admin initial, seede automatiquement
    depuis INITIAL_ADMIN_PASSWORD (voir scripts/seed_admin.py) et qu'il n'y
    avait auparavant aucun moyen de changer sans modifier la base a la main."""
    if not verify_password(payload.current_password, current_user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Mot de passe actuel incorrect")

    current_user.hashed_password = hash_password(payload.new_password)
    await db.commit()
