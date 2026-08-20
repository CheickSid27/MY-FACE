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
    photo_ids: list[uuid.UUID]


class ClusterListResponse(BaseModel):
    clusters: list[FaceCluster]
    unclustered_count: int
