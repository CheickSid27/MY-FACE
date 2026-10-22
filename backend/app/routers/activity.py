"""Volet Statistiques de MYFACE Pro : toutes les actions realisees sur
MYFACE (voir services/activity.py), filtrables et exportables en CSV.
L'equipe MYFACE voit tout ; un photographe voit ses propres actions et
celles qui touchent ses evenements (selfies, telechargements...)."""

import csv
import io
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import Select, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.deps import get_current_user
from app.models.activity_log import ActivityLog
from app.models.user import User, UserRole
from app.services.activity import ACTIONS

router = APIRouter(prefix="/activity", tags=["activity"])

PAGE_SIZE = 50
EXPORT_LIMIT = 50_000


class ActivityRow(BaseModel):
    id: uuid.UUID
    at: datetime
    action: str
    label: str
    actor: str
    event_id: uuid.UUID | None
    event_name: str | None
    details: dict | None


class ActivityPage(BaseModel):
    items: list[ActivityRow]
    total: int
    counts: dict[str, int]
    actions: dict[str, str]


def _filtered(
    user: User,
    action: str | None,
    event_id: uuid.UUID | None,
    start: datetime | None,
    end: datetime | None,
    q: str | None,
) -> Select:
    query = select(ActivityLog)
    if user.role != UserRole.ADMIN:
        query = query.where(or_(ActivityLog.actor_id == user.id, ActivityLog.owner_id == user.id))
    if action:
        query = query.where(ActivityLog.action == action)
    if event_id:
        query = query.where(ActivityLog.event_id == event_id)
    if start:
        query = query.where(ActivityLog.at >= start)
    if end:
        query = query.where(ActivityLog.at < end)
    if q and q.strip():
        like = f"%{q.strip()}%"
        query = query.where(or_(ActivityLog.actor_label.ilike(like), ActivityLog.event_name.ilike(like)))
    return query


def _row(log: ActivityLog) -> ActivityRow:
    return ActivityRow(
        id=log.id,
        at=log.at,
        action=log.action,
        label=ACTIONS.get(log.action, log.action),
        actor=log.actor_label,
        event_id=log.event_id,
        event_name=log.event_name,
        details=log.details,
    )


@router.get("", response_model=ActivityPage)
async def list_activity(
    action: str | None = Query(default=None, max_length=40),
    event_id: uuid.UUID | None = None,
    start: datetime | None = None,
    end: datetime | None = None,
    q: str | None = Query(default=None, max_length=100),
    page: int = Query(default=1, ge=1),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ActivityPage:
    base = _filtered(current_user, action, event_id, start, end, q)
    total = (await db.execute(select(func.count()).select_from(base.subquery()))).scalar_one()
    # Compteurs par action sur la periode (sans le filtre d'action, pour
    # voir la repartition complete).
    by_action = _filtered(current_user, None, event_id, start, end, q).subquery()
    counts = dict(
        (await db.execute(select(by_action.c.action, func.count()).group_by(by_action.c.action))).all()
    )
    logs = (
        await db.execute(base.order_by(ActivityLog.at.desc()).offset((page - 1) * PAGE_SIZE).limit(PAGE_SIZE))
    ).scalars().all()
    return ActivityPage(items=[_row(log) for log in logs], total=total, counts=counts, actions=ACTIONS)


@router.get("/export.csv")
async def export_activity(
    action: str | None = Query(default=None, max_length=40),
    event_id: uuid.UUID | None = None,
    start: datetime | None = None,
    end: datetime | None = None,
    q: str | None = Query(default=None, max_length=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """Export CSV (separateur « ; », lisible directement par Excel)."""
    logs = (
        await db.execute(
            _filtered(current_user, action, event_id, start, end, q).order_by(ActivityLog.at.desc()).limit(EXPORT_LIMIT)
        )
    ).scalars().all()
    buffer = io.StringIO()
    buffer.write("﻿")  # accents corrects a l'ouverture dans Excel
    writer = csv.writer(buffer, delimiter=";")
    writer.writerow(["Date", "Heure", "Action", "Qui", "Événement", "Détails"])
    for log in logs:
        details = ", ".join(f"{k} : {v}" for k, v in (log.details or {}).items())
        writer.writerow(
            [
                log.at.strftime("%d/%m/%Y"),
                log.at.strftime("%H:%M:%S"),
                ACTIONS.get(log.action, log.action),
                log.actor_label,
                log.event_name or "",
                details,
            ]
        )
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="myface-activite.csv"'},
    )
