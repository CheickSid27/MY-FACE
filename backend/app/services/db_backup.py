"""Envoi des sauvegardes de la base dans Cloudflare R2 (04/11).

La base vit sur le PC (service « db ») : le service « db-sauvegarde » en fait
une copie complete chaque nuit dans ./sauvegardes (monte ici en lecture seule
sur /sauvegardes). Toutes les heures, on envoie dans R2 les copies pas encore
envoyees, sous « sauvegardes/<nom>.dump » (bucket prive) : si le disque du PC
lache, la base se recharge depuis R2. Les copies de plus de 14 jours sont
retirees de R2 comme du disque.
"""

import asyncio
import datetime as dt
import logging
import re
from pathlib import Path

from app.services.storage import StorageService

logger = logging.getLogger("myface.sauvegardes")

DOSSIER = Path("/sauvegardes")
PREFIXE_R2 = "sauvegardes/"
GARDER_JOURS = 14
_NOM = re.compile(r"^myface-(\d{8})-(\d{4})\.dump$")


async def envoyer_sauvegardes(storage: StorageService) -> int:
    """Envoie les copies locales absentes de R2. Renvoie le nombre envoye."""
    if not DOSSIER.is_dir():
        return 0
    envoyees = 0
    limite = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=GARDER_JOURS)
    for fichier in sorted(DOSSIER.glob("myface-*.dump")):
        m = _NOM.match(fichier.name)
        if not m:
            continue
        date = dt.datetime.strptime(m.group(1) + m.group(2), "%Y%m%d%H%M").replace(tzinfo=dt.timezone.utc)
        cle = PREFIXE_R2 + fichier.name
        if date < limite:
            if await storage.exists(cle):
                await storage.delete(cle)
            continue
        if await storage.exists(cle):
            continue
        donnees = await asyncio.to_thread(fichier.read_bytes)
        await storage.upload(cle, donnees, "application/octet-stream")
        envoyees += 1
        logger.info("Sauvegarde envoyee dans R2 : %s (%d Ko)", fichier.name, len(donnees) // 1024)
    return envoyees


async def backup_upload_loop(storage: StorageService) -> None:
    """Premier passage 2 minutes apres le demarrage, puis toutes les heures."""
    await asyncio.sleep(120)
    while True:
        try:
            await envoyer_sauvegardes(storage)
        except Exception:
            logger.exception("Envoi des sauvegardes dans R2 : echec")
        await asyncio.sleep(3600)
