"""Cree le compte admin initial a partir de INITIAL_ADMIN_EMAIL / INITIAL_ADMIN_PASSWORD.

Usage (depuis le conteneur backend ou un venv local) :
    python -m scripts.seed_admin
"""

import asyncio
from datetime import datetime, timezone

from sqlalchemy import func, select

from app.core.config import get_settings
from app.core.database import AsyncSessionLocal
from app.core.security import hash_password
from app.models.user import User, UserRole

settings = get_settings()


async def seed_admin() -> None:
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(User).where(func.lower(User.email) == settings.initial_admin_email.lower())
        )
        existing = result.scalar_one_or_none()

        if existing is not None:
            print(f"Admin '{settings.initial_admin_email}' existe deja, rien a faire.")
            return

        admin = User(
            email=settings.initial_admin_email.lower(),
            hashed_password=hash_password(settings.initial_admin_password),
            role=UserRole.ADMIN,
            email_verified_at=datetime.now(timezone.utc),
        )
        db.add(admin)
        await db.commit()
        print(f"Admin cree : {settings.initial_admin_email}")


if __name__ == "__main__":
    asyncio.run(seed_admin())
