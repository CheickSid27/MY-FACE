"""Verifie les migrations Alembic sur une base locale jetable, jamais sur la
base de production : cree la base `myface_migrations` sur le Postgres local
des tests (meme serveur que TEST_DATABASE_URL), applique toutes les
migrations, revient d'une version en arriere, remonte, puis supprime la base.

    docker compose run --rm --no-deps -w /app backend python3 -m scripts.verifier_migrations
"""

import asyncio
import os
import subprocess
import sys

import asyncpg

from app.core.config import get_settings

NOM = "myface_migrations"


def _url_serveur(url: str) -> str:
    return url.replace("postgresql+asyncpg://", "postgresql://").rsplit("/", 1)[0]


async def _recreer(serveur: str, supprimer_seulement: bool = False) -> None:
    conn = await asyncpg.connect(f"{serveur}/postgres")
    try:
        await conn.execute(f'DROP DATABASE IF EXISTS "{NOM}"')
        if not supprimer_seulement:
            await conn.execute(f'CREATE DATABASE "{NOM}"')
    finally:
        await conn.close()


def _alembic(env: dict, *args: str) -> None:
    print("alembic", *args, flush=True)
    subprocess.run([sys.executable, "-m", "alembic", *args], check=True, env=env)


def main() -> None:
    test_url = get_settings().test_database_url
    if not test_url or "neon" in test_url:
        sys.exit("TEST_DATABASE_URL doit pointer vers le Postgres local des tests")
    serveur = _url_serveur(test_url)
    asyncio.run(_recreer(serveur))
    env = {**os.environ, "DATABASE_URL": f"{test_url.rsplit('/', 1)[0]}/{NOM}"}
    try:
        _alembic(env, "upgrade", "head")
        _alembic(env, "downgrade", "-1")
        _alembic(env, "upgrade", "head")
        print("Migrations OK")
    finally:
        asyncio.run(_recreer(serveur, supprimer_seulement=True))


if __name__ == "__main__":
    main()
