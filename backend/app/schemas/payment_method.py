import uuid

from pydantic import BaseModel

from app.models.order import PaymentMethod


class EventPaymentMethodRead(BaseModel):
    id: uuid.UUID
    method: PaymentMethod
    phone_number: str
    qr_image_url: str

    model_config = {"from_attributes": True}
