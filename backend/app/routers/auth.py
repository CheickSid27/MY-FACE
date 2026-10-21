import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db
from app.core.security import (
    InvalidTokenError,
    TokenType,
    burn_password_check,
    create_access_token,
    create_email_verification_token,
    create_password_reset_token,
    create_refresh_token,
    decode_token_payload,
    hash_password,
    issued_before,
    secret_fingerprint,
    verify_password,
)
from app.deps import ACCOUNT_SUSPENDED_DETAIL, SESSION_REVOKED_DETAIL, get_current_user
from app.models.user import User, UserRole
from app.schemas.auth import (
    AccessTokenResponse,
    ForgotPasswordRequest,
    LoginRequest,
    PasswordChangeRequest,
    RefreshRequest,
    RegisterRequest,
    ResetPasswordRequest,
    TokenResponse,
    VerifyEmailRequest,
)
from app.schemas.user import UserProfileUpdate, UserRead
from app.services.email import (
    EmailService,
    get_email_service,
    password_reset_email,
    verification_email,
)
from app.services.rate_limit import client_ip, limiter

# Inscriptions par adresse : assez pour un studio qui cree plusieurs comptes,
# trop peu pour remplir la base de comptes factices.
REGISTER_LIMIT_PER_HOUR = 10
# Connexion : essais par adresse IP et par compte sur 15 minutes (nginx
# limite deja le debit, ceci couvre un acces direct au backend).
LOGIN_LIMIT_PER_IP = 20
LOGIN_LIMIT_PER_EMAIL = 10
LOGIN_WINDOW_SECONDS = 15 * 60
# Liens par e-mail : de quoi reessayer, pas de quoi inonder une boite.
EMAIL_LINKS_PER_HOUR = 3
FORGOT_PASSWORD_PER_IP_PER_HOUR = 10

FORGOT_PASSWORD_MESSAGE = (
    "Si un compte existe avec cette adresse, un e-mail vient de partir avec un lien "
    "pour choisir un nouveau mot de passe."
)
INVALID_LINK_DETAIL = "Lien invalide ou expiré : redemandez-en un nouveau"

router = APIRouter(prefix="/auth", tags=["auth"])


def _tokens_for(user: User) -> TokenResponse:
    subject = str(user.id)
    return TokenResponse(
        access_token=create_access_token(subject),
        refresh_token=create_refresh_token(subject),
    )


async def _send_verification(user: User, email_service: EmailService) -> None:
    token = create_email_verification_token(str(user.id), user.email)
    link = f"{get_settings().app_base_url}/verifier-email?token={token}"
    await email_service.send(verification_email(user.email, user.display_name, link))


async def _user_from_link(token: str, token_type: TokenType, db: AsyncSession) -> tuple[User, dict]:
    try:
        payload = decode_token_payload(token, token_type)
        user_id = uuid.UUID(payload["sub"])
    except (InvalidTokenError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=INVALID_LINK_DETAIL) from exc
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=INVALID_LINK_DETAIL)
    return user, payload


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, request: Request, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    email = payload.email.lower()
    limiter.check("login-ip", client_ip(request), LOGIN_LIMIT_PER_IP, LOGIN_WINDOW_SECONDS)
    limiter.check("login-email", email, LOGIN_LIMIT_PER_EMAIL, LOGIN_WINDOW_SECONDS, record=False)

    result = await db.execute(select(User).where(func.lower(User.email) == email))
    user = result.scalars().first()

    if user is None:
        burn_password_check(payload.password)
    if user is None or not verify_password(payload.password, user.hashed_password):
        limiter.hit("login-email", email)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="E-mail ou mot de passe incorrect")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=ACCOUNT_SUSPENDED_DETAIL)

    return _tokens_for(user)


@router.post("/refresh", response_model=AccessTokenResponse)
async def refresh(payload: RefreshRequest, db: AsyncSession = Depends(get_db)) -> AccessTokenResponse:
    try:
        token_payload = decode_token_payload(payload.refresh_token, TokenType.REFRESH)
        user_id = uuid.UUID(token_payload["sub"])
    except InvalidTokenError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token invalide") from exc

    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Utilisateur introuvable")
    if issued_before(token_payload, user.password_changed_at):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=SESSION_REVOKED_DETAIL)
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=ACCOUNT_SUSPENDED_DETAIL)

    return AccessTokenResponse(access_token=create_access_token(str(user.id)))


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    payload: RegisterRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    email_service: EmailService = Depends(get_email_service),
) -> TokenResponse:
    """Inscription libre d'un photographe : compte cree et connecte tout de
    suite (memes conditions que Fokevani), chaque nouvel evenement demarre
    au pack Decouverte (10 photos, gratuit). Un e-mail de confirmation part
    aussitot : tant que l'adresse n'est pas confirmee, le photographe ne
    cree ni evenement ni pack (voir deps.require_verified_user)."""
    limiter.check("register", client_ip(request), REGISTER_LIMIT_PER_HOUR, 3600)

    email = payload.email.lower()
    existing = await db.execute(select(User.id).where(func.lower(User.email) == email))
    if existing.first() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Un compte existe déjà avec cet e-mail : connectez-vous",
        )

    user = User(
        email=email,
        hashed_password=hash_password(payload.password),
        role=UserRole.PHOTOGRAPHE,
        display_name=payload.display_name,
        studio_name=(payload.studio_name or "").strip() or None,
        phone=payload.phone,
        city=(payload.city or "").strip() or None,
        terms_accepted_at=datetime.now(timezone.utc),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    background_tasks.add_task(_send_verification, user, email_service)
    return _tokens_for(user)


@router.post("/verify-email")
async def verify_email(payload: VerifyEmailRequest, db: AsyncSession = Depends(get_db)) -> dict[str, str]:
    """Lien de confirmation recu par e-mail. Sans connexion : le lien peut
    etre ouvert sur un autre appareil que celui de l'inscription."""
    user, token_payload = await _user_from_link(payload.token, TokenType.EMAIL_VERIFY, db)
    if token_payload.get("email") != user.email.lower():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=INVALID_LINK_DETAIL)
    if user.email_verified_at is None:
        user.email_verified_at = datetime.now(timezone.utc)
        await db.commit()
    return {"status": "verified", "email": user.email}


@router.post("/resend-verification")
async def resend_verification(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    email_service: EmailService = Depends(get_email_service),
) -> dict[str, str]:
    if current_user.email_verified:
        return {"status": "already_verified"}
    limiter.check("verify-email", str(current_user.id), EMAIL_LINKS_PER_HOUR, 3600)
    background_tasks.add_task(_send_verification, current_user, email_service)
    return {"status": "sent"}


@router.post("/forgot-password", status_code=status.HTTP_202_ACCEPTED)
async def forgot_password(
    payload: ForgotPasswordRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    email_service: EmailService = Depends(get_email_service),
) -> dict[str, str]:
    """Meme reponse que le compte existe ou non : la page ne doit pas
    permettre de tester quelles adresses sont inscrites."""
    email = payload.email.lower()
    limiter.check("forgot-ip", client_ip(request), FORGOT_PASSWORD_PER_IP_PER_HOUR, 3600)
    limiter.check("forgot-email", email, EMAIL_LINKS_PER_HOUR, 3600)

    result = await db.execute(select(User).where(func.lower(User.email) == email))
    user = result.scalars().first()
    if user is not None and user.is_active:
        token = create_password_reset_token(str(user.id), user.hashed_password)
        link = f"{get_settings().app_base_url}/reinitialiser-mot-de-passe?token={token}"
        background_tasks.add_task(
            email_service.send, password_reset_email(user.email, user.display_name, link)
        )
    return {"detail": FORGOT_PASSWORD_MESSAGE}


@router.post("/reset-password", status_code=status.HTTP_204_NO_CONTENT)
async def reset_password(payload: ResetPasswordRequest, db: AsyncSession = Depends(get_db)) -> None:
    user, token_payload = await _user_from_link(payload.token, TokenType.PASSWORD_RESET, db)
    if token_payload.get("pwd") != secret_fingerprint(user.hashed_password):
        # mot de passe deja change depuis l'envoi du lien : lien deja utilise
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=INVALID_LINK_DETAIL)
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=ACCOUNT_SUSPENDED_DETAIL)

    now = datetime.now(timezone.utc)
    user.hashed_password = hash_password(payload.new_password)
    user.password_changed_at = now
    # le lien est arrive dans sa boite : l'adresse est donc la sienne
    if user.email_verified_at is None:
        user.email_verified_at = now
    await db.commit()


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


@router.post("/password", response_model=TokenResponse)
async def change_password(
    payload: PasswordChangeRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Changer son propre mot de passe (y compris le mot de passe admin
    initial, seede depuis INITIAL_ADMIN_PASSWORD). Les autres sessions
    ouvertes avec l'ancien mot de passe sont fermees ; celle-ci recoit de
    nouveaux jetons et reste connectee."""
    if not verify_password(payload.current_password, current_user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Mot de passe actuel incorrect")

    current_user.hashed_password = hash_password(payload.new_password)
    current_user.password_changed_at = datetime.now(timezone.utc)
    await db.commit()
    return _tokens_for(current_user)
