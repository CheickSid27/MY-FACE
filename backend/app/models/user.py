import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    PHOTOGRAPHE = "photographe"


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role", values_callable=lambda enum_cls: [e.value for e in enum_cls]),
        nullable=False,
        default=UserRole.PHOTOGRAPHE,
    )
    # Profil du photographe (compte cree par inscription libre, voir
    # routers/auth.py register) : nom affiche aux invites sur la page de
    # l'evenement et dans le filigrane par defaut des packs payants.
    display_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    studio_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    city: Mapped[str | None] = mapped_column(String(120), nullable=True)
    # Compte suspendu par un admin : plus de connexion ni d'appel authentifie
    # (voir deps.get_current_user), ses evenements restent en ligne.
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true", nullable=False)
    terms_accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Adresse e-mail confirmee (lien recu par e-mail, voir routers/auth.py).
    # Vide = pas encore confirmee : le photographe se connecte mais ne cree
    # ni evenement ni pack tant qu'il ne l'a pas fait (voir deps.py).
    email_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Dernier changement de mot de passe : les sessions ouvertes avant sont
    # refusees (un mot de passe change ou reinitialise deconnecte partout).
    password_changed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    @property
    def public_name(self) -> str | None:
        """Nom montre aux invites : le studio s'il est renseigne, sinon le nom."""
        return (self.studio_name or self.display_name or "").strip() or None

    @property
    def email_verified(self) -> bool:
        return self.email_verified_at is not None
