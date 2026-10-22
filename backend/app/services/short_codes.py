"""Code court des evenements : 8 caracteres aleatoires, affiches en deux
groupes (« K7M2-QX9P »), pour une adresse simple a lire, a dire au micro et a
taper (app.myfaceci.online/e/K7M2QX9P) ; l'identifiant long reste interne.

Sans 0/O, 1/I/L (confondus a la lecture) : 31 signes, 31^8 = 852 milliards
de codes. Meme avec des milliers d'evenements, un curieux qui essaierait des
codes au hasard (limite par IP dans nginx) ne tomberait sur aucune galerie."""

import secrets

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.event import Event

ALPHABET = "23456789ABCDEFGHJKMNPQRSTUVWXYZ"
LENGTH = 8


def random_code() -> str:
    return "".join(secrets.choice(ALPHABET) for _ in range(LENGTH))


def normalize_code(raw: str) -> str | None:
    """Code saisi par un invite (minuscules, tiret, espaces) -> code stocke,
    ou None s'il ne peut pas etre un code."""
    code = "".join(ch for ch in raw.upper() if ch not in " -._")
    if len(code) != LENGTH or any(ch not in ALPHABET for ch in code):
        return None
    return code


async def new_short_code(db: AsyncSession) -> str:
    while True:
        code = random_code()
        if (await db.execute(select(Event.id).where(Event.short_code == code))).first() is None:
            return code
