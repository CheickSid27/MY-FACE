"""Refait les apercus filigranes dont le texte contient des lettres accentuees
(ex : studio « Sidibé »), dessinees en carres avant l'ajout de la police DejaVu.

    docker compose exec backend python3 scripts/refaire_filigranes_accents.py
"""

import asyncio

from sqlalchemy import select

from app.core.database import get_session_factory
from app.models.event import Event
from app.services.face_clusters import face_cluster_cache
from app.services.packs import get_owner, watermark_text_for
from app.services.storage import get_storage_service
from app.services.watermark import regenerate_event_watermarks


async def main() -> None:
    factory = get_session_factory()
    storage = get_storage_service()
    async with factory() as db:
        events = (await db.execute(select(Event))).scalars().all()
        todo = []
        for event in events:
            text = watermark_text_for(event, await get_owner(db, event))
            if not text.isascii():
                todo.append((event.id, event.name, text))
    print(f"{len(todo)} evenement(s) a refaire")
    for event_id, name, text in todo:
        n = await regenerate_event_watermarks(event_id, text, storage, factory, face_cluster_cache.invalidate)
        print(f"  {name} : {n} apercu(s) refait(s) avec « {text} »")


if __name__ == "__main__":
    asyncio.run(main())
