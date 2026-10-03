import uuid
from datetime import datetime

from pydantic import BaseModel


class DownloadPhoto(BaseModel):
    photo_id: uuid.UUID
    filename: str
    # Original en qualite d'origine, servi en telechargement (Content-
    # Disposition: attachment) : c'est le fichier que le client achete.
    url: str
    # Miniature pour l'affichage de la grille : afficher les originaux
    # (plusieurs Mo chacun) faisait telecharger des dizaines de Mo au
    # telephone du client rien que pour voir la liste.
    thumbnail_url: str
    print_requested: bool = False


class DownloadResponse(BaseModel):
    order_id: uuid.UUID
    event_id: uuid.UUID
    photos: list[DownloadPhoto]
    # Duree de validite des URLs signees ci-dessus (pas de l'acces a la
    # commande, qui reste permanent : la page les regenere a la demande).
    expires_in: int
    # Derniere impression des tirages papier (page d'impression : evite
    # d'imprimer deux fois par erreur).
    printed_at: datetime | None = None
    # Photos offertes par l'organisateur (pas de « paiement confirme »)
    offert: bool = False


class PrintedResponse(BaseModel):
    printed_at: datetime
