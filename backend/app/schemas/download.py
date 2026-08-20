import uuid

from pydantic import BaseModel


class DownloadPhoto(BaseModel):
    photo_id: uuid.UUID
    filename: str
    url: str


class DownloadResponse(BaseModel):
    order_id: uuid.UUID
    photos: list[DownloadPhoto]
    expires_in: int
