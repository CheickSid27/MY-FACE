import asyncio
import uuid
from datetime import datetime, timezone

import httpx
from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Request, Response, UploadFile, status
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
from app.deps import ACCOUNT_SUSPENDED_DETAIL, SESSION_REVOKED_DETAIL, get_current_user, require_verified_user
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
from app.schemas.user import PayoutRead, PayoutUpdate, UserProfileUpdate, UserRead
from app.services import paystack
from app.services.avatars import AVATAR_CONTENT_TYPES, AVATAR_MAX_BYTES, avatar_key, make_avatar
from app.services.email import (
    EmailService,
    get_email_service,
    password_reset_email,
    verification_email,
)
from app.services.phone import normalize_phone_or_ci
from app.services.rate_limit import client_ip, limiter
from app.services.storage import StorageService, get_storage_service
from app.services.thumbnails import InvalidImageError

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


def _payout_read(user: User) -> PayoutRead:
    account = user.payout_account or ""
    masked = f"•• {account[-4:]}" if account else None
    return PayoutRead(
        enabled=bool(user.payout_enabled and user.paystack_subaccount_code),
        method=user.payout_method,
        account_masked=masked,
        name=user.payout_name,
        available=paystack.is_configured(),
    )


@router.get("/me/payout", response_model=PayoutRead)
async def get_payout(current_user: User = Depends(get_current_user)) -> PayoutRead:
    return _payout_read(current_user)


@router.put("/me/payout", response_model=PayoutRead)
async def save_payout(
    payload: PayoutUpdate,
    current_user: User = Depends(require_verified_user),
    db: AsyncSession = Depends(get_db),
) -> PayoutRead:
    """Le photographe active le paiement en ligne de ses ventes : Paystack lui
    verse directement l'argent (sur son Wave, Orange Money, MTN ou compte
    bancaire), sans commission MYFACE, frais Paystack deduits."""
    if not paystack.is_configured():
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Paiement en ligne indisponible")
    account = payload.account.replace(" ", "").replace(".", "").replace("-", "")
    if payload.method == "bank":
        if not payload.bank_code:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Choisissez votre banque")
        if len(account) != 24:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Le RIB fait 24 caractères (sans « CI » et les 2 chiffres de l'IBAN)",
            )
        bank = payload.bank_code
    else:
        try:
            international = normalize_phone_or_ci(account)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        if not international.startswith("+225"):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Numéro de Côte d'Ivoire uniquement")
        # Paystack attend le numero local a 10 chiffres (07 01 02 03 04)
        account = international.removeprefix("+225")
        bank = paystack.PAYOUT_BANK_CODES[payload.method]
    try:
        code = await paystack.save_subaccount(
            current_user.paystack_subaccount_code,
            business_name=payload.name.strip(),
            settlement_bank=bank,
            account_number=account,
            description=f"Photographe MYFACE {current_user.email}",
        )
    except (paystack.PaystackError, httpx.HTTPError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Paystack a refusé ces informations : {exc}",
        ) from exc
    current_user.paystack_subaccount_code = code
    current_user.payout_method = payload.method
    current_user.payout_account = account
    current_user.payout_name = payload.name.strip()
    current_user.payout_enabled = True
    await db.commit()
    await db.refresh(current_user)
    return _payout_read(current_user)


@router.delete("/me/payout", response_model=PayoutRead)
async def disable_payout(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PayoutRead:
    """Retour au paiement direct (QR + confirmation) sur ses evenements."""
    current_user.payout_enabled = False
    await db.commit()
    await db.refresh(current_user)
    return _payout_read(current_user)


@router.post("/me/avatar", response_model=UserRead)
async def upload_avatar(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    storage: StorageService = Depends(get_storage_service),
) -> User:
    """Photo de profil : recadree en carre 512 px. Remplace la precedente."""
    if file.content_type not in AVATAR_CONTENT_TYPES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Photo en JPEG, PNG ou WebP")
    data = await file.read(AVATAR_MAX_BYTES + 1)
    if len(data) > AVATAR_MAX_BYTES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Photo trop lourde (8 Mo maximum)")
    try:
        avatar = await asyncio.to_thread(make_avatar, data)
    except InvalidImageError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Image illisible") from exc

    old_key = current_user.avatar_key
    new_key = avatar_key(current_user.id)
    await storage.upload(new_key, avatar, "image/jpeg")
    current_user.avatar_key = new_key
    await db.commit()
    await db.refresh(current_user)
    if old_key:
        await storage.delete(old_key)
    return current_user


@router.delete("/me/avatar", response_model=UserRead)
async def delete_avatar(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    storage: StorageService = Depends(get_storage_service),
) -> User:
    old_key = current_user.avatar_key
    current_user.avatar_key = None
    await db.commit()
    await db.refresh(current_user)
    if old_key:
        await storage.delete(old_key)
    return current_user


@router.get("/avatars/{user_id}", include_in_schema=False)
async def get_avatar(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    storage: StorageService = Depends(get_storage_service),
) -> Response:
    """Photo de profil (publique : affichee aux invites a cote du nom du
    photographe). Adresse versionnee : gardee en cache une semaine."""
    user = await db.get(User, user_id)
    if user is None or not user.avatar_key:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pas de photo de profil")
    data = await storage.download(user.avatar_key)
    return Response(content=data, media_type="image/jpeg", headers={"Cache-Control": "public, max-age=604800, immutable"})


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
