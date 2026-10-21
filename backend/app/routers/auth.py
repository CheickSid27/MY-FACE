import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func, select
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
from app.deps import ACCOUNT_SUSPENDED_DETAIL, get_current_user
from app.models.user import User, UserRole
from app.schemas.auth import (
    AccessTokenResponse,
    LoginRequest,
    PasswordChangeRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
)
from app.schemas.user import UserProfileUpdate, UserRead
from app.services.rate_limit import client_ip, limiter

# Inscriptions par adresse : assez pour un studio qui cree plusieurs comptes,
# trop peu pour remplir la base de comptes factices.
REGISTER_LIMIT_PER_HOUR = 10

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    result = await db.execute(select(User).where(func.lower(User.email) == payload.email.lower()))
    user = result.scalars().first()

    if user is None or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Email ou mot de passe incorrect")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=ACCOUNT_SUSPENDED_DETAIL)

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
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=ACCOUNT_SUSPENDED_DETAIL)

    return AccessTokenResponse(access_token=create_access_token(subject))


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    payload: RegisterRequest, request: Request, db: AsyncSession = Depends(get_db)
) -> TokenResponse:
    """Inscription libre d'un photographe : compte cree et connecte tout de
    suite, sans carte ni validation (memes conditions que Fokevani). Chaque
    nouvel evenement demarre au pack Decouverte (10 photos, gratuit)."""
    limiter.check("register", client_ip(request), REGISTER_LIMIT_PER_HOUR, 3600)

    email = payload.email.lower()
    existing = await db.execute(select(User.id).where(func.lower(User.email) == email))
    if existing.first() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Un compte existe deja avec cet email : connectez-vous",
        )

    user = User(
        email=email,
        hashed_password=hash_password(payload.password),
        role=UserRole.PHOTOGRAPHE,
        display_name=payload.display_name.strip(),
        studio_name=(payload.studio_name or "").strip() or None,
        phone=payload.phone,
        city=(payload.city or "").strip() or None,
        terms_accepted_at=datetime.now(timezone.utc),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    subject = str(user.id)
    return TokenResponse(
        access_token=create_access_token(subject),
        refresh_token=create_refresh_token(subject),
    )


@router.get("/me", response_model=UserRead)
async def me(current_user: User = Depends(get_current_user)) -> User:
    return current_user


@router.patch("/me", response_model=UserRead)
async def update_me(
    payload: UserProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Profil du photographe : nom, studio (affiche aux invites et dans le
    filigrane), telephone, ville."""
    for field, value in payload.model_dump(exclude_unset=True).items():
        if isinstance(value, str):
            value = value.strip() or None
        if field == "display_name" and value is None:
            continue
        setattr(current_user, field, value)
    await db.commit()
    await db.refresh(current_user)
    return current_user


@router.post("/password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(
    payload: PasswordChangeRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Permet a un utilisateur deja authentifie de changer son propre mot de
    passe, notamment le mot de passe admin initial, seede automatiquement
    depuis INITIAL_ADMIN_PASSWORD (voir scripts/seed_admin.py) et qu'il n'y
    avait auparavant aucun moyen de changer sans modifier la base a la main."""
    if not verify_password(payload.current_password, current_user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Mot de passe actuel incorrect")

    current_user.hashed_password = hash_password(payload.new_password)
    await db.commit()
