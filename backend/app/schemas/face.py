import uuid

from pydantic import BaseModel, ConfigDict

from app.models.photo import IndexingStatus
from app.schemas.photo import PhotoRead


class FaceScanMatch(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    photo: PhotoRead
    similarity: float


class FaceScanResponse(BaseModel):
    matches: list[FaceScanMatch]
    faces_detected_in_selfie: int


class PhotoIndexingStatus(BaseModel):
    photo_id: uuid.UUID
    indexing_status: IndexingStatus


class FaceCluster(BaseModel):
    cluster_id: int
    photo_count: int
    representative_photo: PhotoRead
    # Vignette recadree sur le visage (pas la photo entiere), pour identifier
    # la personne d'un coup d'oeil dans la vue "personnes detectees".
    representative_face_url: str
    # Photos completes (pas juste des IDs) : evite au frontend de devoir
    # re-recuperer les photos via une liste paginee a part (qui tronquait
    # silencieusement les clusters au-dela des 200 premieres photos de
    # l'evenement, voir historique). Le backend a deja chaque Photo en main
    # ici (meme jointure que pour le clustering), donc aucun cout supplementaire.
    photos: list[PhotoRead]


class ClusterListResponse(BaseModel):
    clusters: list[FaceCluster]
    unclustered_count: int
