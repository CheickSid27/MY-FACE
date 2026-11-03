import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class SectionRead(BaseModel):
    """Partie d'un evenement (mairie, reception...), vue invite et admin."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    starts_at: datetime | None = None
    location: str | None = None
    position: int = 0
    photo_count: int = 0


class SectionCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=120)
    starts_at: datetime | None = None
    location: str | None = Field(default=None, max_length=255)


class SectionUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str | None = Field(default=None, min_length=1, max_length=120)
    starts_at: datetime | None = None
    location: str | None = Field(default=None, max_length=255)
    position: int | None = Field(default=None, ge=0, le=1000)


class PhotosSectionUpdate(BaseModel):
    """Ranger des photos dans une partie (section_id None = les sortir de leur partie)."""

    photo_ids: list[uuid.UUID] = Field(min_length=1, max_length=2000)
    section_id: uuid.UUID | None = None


class PhotosSectionResult(BaseModel):
    moved: int
