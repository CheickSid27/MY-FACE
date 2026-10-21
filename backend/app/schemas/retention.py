import uuid
from datetime import datetime

from pydantic import BaseModel


class ExpiredEventRead(BaseModel):
    event_id: uuid.UUID
    name: str
    date: datetime
    photo_count: int


class RetentionReportRead(BaseModel):
    """Ce que la suppression automatique supprime (ou supprimerait, en
    simulation) a son prochain passage."""

    enabled: bool
    photo_days: int
    order_days: int
    events: list[ExpiredEventRead]
    orders_to_anonymize: int
    photos_deleted: int = 0
    orders_anonymized: int = 0


class RetentionExemptUpdate(BaseModel):
    exempt: bool
