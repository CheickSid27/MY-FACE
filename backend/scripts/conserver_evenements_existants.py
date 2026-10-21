"""Exempte de la suppression automatique tous les evenements deja en base.

A lancer une fois, juste avant d'activer RETENTION_ENABLED : les evenements
crees avant la mise en place de la conservation des donnees (demo du site,
evenements de test) gardent leurs photos ; seuls les evenements crees
ensuite suivent la regle des 90 jours. Un admin peut rendre la regle a un
evenement depuis sa page (« Appliquer la duree normale »).

Usage (depuis le conteneur backend) :
    python3 -m scripts.conserver_evenements_existants
"""

import asyncio

from sqlalchemy import func, select, update

from app.core.database import AsyncSessionLocal
from app.models.event import Event
from app.models.photo import Photo


async def conserver() -> None:
    async with AsyncSessionLocal() as db:
        lignes = await db.execute(
            select(Event.name, Event.date, func.count(Photo.id))
            .outerjoin(Photo, Photo.event_id == Event.id)
            .where(Event.retention_exempt.is_(False))
            .group_by(Event.id)
            .order_by(Event.date)
        )
        evenements = lignes.all()
        resultat = await db.execute(
            update(Event).where(Event.retention_exempt.is_(False)).values(retention_exempt=True)
        )
        await db.commit()

    for nom, date, photos in evenements:
        print(f"  conserve : {nom} ({date:%d/%m/%Y}, {photos} photos)")
    print(f"{resultat.rowcount} evenement(s) exempte(s) de la suppression automatique")


if __name__ == "__main__":
    asyncio.run(conserver())
