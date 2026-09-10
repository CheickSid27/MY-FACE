import uuid

from pydantic import BaseModel, Field


class GeniusPayInitRequest(BaseModel):
    session_id: uuid.UUID
    contact_phone: str = Field(min_length=6, max_length=32)


class GeniusPayInitResponse(BaseModel):
    order_id: uuid.UUID
    checkout_url: str
    status: str
    environment: str
