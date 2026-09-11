from datetime import date

from pydantic import BaseModel


class DailySales(BaseModel):
    date: date
    revenue: float
    order_count: int


class EventStats(BaseModel):
    event_id: str
    photo_count: int
    photos_indexed: int
    photos_pending: int
    orders_pending: int
    orders_processing: int
    orders_awaiting_confirmation: int
    orders_success: int
    orders_failed: int
    orders_cancelled: int
    total_revenue: float
    currency: str
    photos_sold: int
    sales_by_day: list[DailySales]
