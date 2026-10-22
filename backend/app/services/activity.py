"""Journal des actions (volet Statistiques de MYFACE Pro).

`log_activity` ajoute une ligne et l'enregistre dans la session de la
requete, apres le travail de la route : un probleme d'ecriture du journal
ne fait jamais echouer l'action elle-meme.
"""

import logging
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.activity_log import ActivityLog
from app.models.event import Event
from app.models.user import User

logger = logging.getLogger("myface.activity")

# Actions connues et leur libelle (meme liste cote interface).
ACTIONS: dict[str, str] = {
    "inscription": "Inscription d'un photographe",
    "email_confirme": "Adresse e-mail confirmée",
    "inscription_annulee": "Inscription annulée (e-mail non confirmé)",
    "connexion": "Connexion",
    "mot_de_passe_change": "Mot de passe changé",
    "mot_de_passe_reinitialise": "Mot de passe réinitialisé",
    "photo_profil": "Photo de profil changée",
    "versements_actives": "Paiement en ligne activé",
    "evenement_cree": "Événement créé",
    "evenement_modifie": "Événement modifié",
    "evenement_supprime": "Événement supprimé",
    "photos_ajoutees": "Photos ajoutées",
    "photo_supprimee": "Photo supprimée",
    "photos_supprimees": "Photos supprimées (plusieurs)",
    "selfie": "Selfie d'un invité",
    "telechargement": "Photos téléchargées par un invité",
    "pack_declare": "Paiement de pack déclaré",
    "pack_paye": "Pack payé en ligne",
    "pack_valide": "Pack validé par MYFACE",
    "pack_refuse": "Pack refusé",
    "compte_cree": "Compte créé par MYFACE",
    "compte_suspendu": "Compte suspendu",
    "compte_reactive": "Compte réactivé",
    "compte_supprime": "Compte supprimé",
}

GUEST = "Invité"


def user_label(user: User | None) -> str:
    if user is None:
        return GUEST
    name = (user.studio_name or user.display_name or "").strip()
    return f"{name} ({user.email})" if name else user.email


async def log_activity(
    db: AsyncSession,
    action: str,
    actor: User | None = None,
    event: Event | None = None,
    details: dict | None = None,
    actor_label: str | None = None,
    actor_id: uuid.UUID | None = None,
) -> None:
    try:
        db.add(
            ActivityLog(
                action=action,
                actor_id=actor.id if actor is not None else actor_id,
                actor_label=(actor_label or user_label(actor))[:160],
                event_id=event.id if event is not None else None,
                event_name=event.name[:200] if event is not None else None,
                owner_id=event.organizer_id if event is not None else None,
                details=details or None,
            )
        )
        await db.commit()
    except Exception:  # noqa: BLE001 - le journal ne doit jamais casser l'action
        logger.exception("Journal : echec d'ecriture de %s", action)
        await db.rollback()
