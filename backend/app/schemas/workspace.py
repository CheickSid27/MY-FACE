"""Espace photographe / admin : accueil, ventes a confirmer de tous les
evenements, fil des notifications (voir routers/workspace.py)."""

import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.order import OrderStatus, PaymentMethod


class LiveEvent(BaseModel):
    id: uuid.UUID
    name: str
    date: datetime
    location: str
    pack: str
    photo_count: int
    photo_limit: int | None
    indexed: int
    to_index: int
    # "live" (aujourd'hui), "upcoming" (a venir), "past" (le plus recent)
    moment: str


class TodoItem(BaseModel):
    kind: str
    title: str
    detail: str
    href: str


class WorkspaceSummary(BaseModel):
    event: LiveEvent | None
    events_count: int
    sales_today: float
    paid_orders_today: int
    orders_to_confirm: int
    currency: str = "XOF"
    todo: list[TodoItem]


class WorkspaceOrder(BaseModel):
    id: uuid.UUID
    event_id: uuid.UUID
    event_name: str
    contact_phone: str
    total_amount: float
    currency: str
    status: OrderStatus
    payment_method: PaymentMethod
    payment_reference: str | None
    photo_count: int
    print_count: int
    created_at: datetime


class ActivityItem(BaseModel):
    id: str
    kind: str
    title: str
    body: str
    href: str
    at: datetime
