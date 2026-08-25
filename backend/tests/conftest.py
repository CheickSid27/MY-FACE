from collections.abc import AsyncGenerator

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import get_settings
from app.core.database import Base, get_db, get_session_factory
from app.main import app
from app.models.user import User, UserRole
from app.services.storage import StorageService, get_storage_service

settings = get_settings()

# DB de test dediee : un Postgres local jetable (docker-compose), toujours
# distinct de DATABASE_URL (qui peut pointer vers Neon en prod) pour ne
# jamais faire tourner la suite de tests contre une base geree a distance.
TEST_DATABASE_URL = settings.test_database_url or (
    settings.database_url.rsplit("/", 1)[0] + "/myface_test"
)

# NullPool : pas de connexion persistante partagee entre tests, evite les
# erreurs asyncpg liees au cycle de vie de l'event loop de pytest-asyncio.
test_engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool)
TestSessionLocal = async_sessionmaker(bind=test_engine, expire_on_commit=False, class_=AsyncSession)


class InMemoryStorageService(StorageService):
    """Double de test pour StorageService : pas d'I/O reseau vers MinIO/Supabase."""

    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}

    async def upload(self, key: str, data: bytes, content_type: str) -> None:
        self.objects[key] = data

    async def delete(self, key: str) -> None:
        self.objects.pop(key, None)

    async def download(self, key: str) -> bytes:
        return self.objects[key]

    async def get_presigned_url(self, key: str, expires_in: int = 3600) -> str:
        return f"http://test-storage.local/{key}?expires_in={expires_in}"

    async def exists(self, key: str) -> bool:
        return key in self.objects


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_test_db():
    from sqlalchemy import text

    async with test_engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await test_engine.dispose()


async def _truncate_all_tables() -> None:
    """Nettoyage entre tests via une connexion neuve et courte, avec
    statement_timeout : si une autre session tient un verrou (tache de fond
    trainante, connexion mal fermee...), on echoue vite et clairement plutot
    que de bloquer indefiniment (observe en pratique lors du developpement)."""
    from sqlalchemy import text

    table_names = ", ".join(f'"{t.name}"' for t in Base.metadata.sorted_tables)
    async with test_engine.connect() as conn:
        await conn.execute(text("SET statement_timeout = '5s'"))
        await conn.execute(text("SET lock_timeout = '5s'"))
        await conn.execute(text(f"TRUNCATE {table_names} RESTART IDENTITY CASCADE"))
        await conn.commit()


@pytest_asyncio.fixture
async def db_session(setup_test_db) -> AsyncGenerator[AsyncSession, None]:
    async with TestSessionLocal() as session:
        yield session
    await _truncate_all_tables()


@pytest_asyncio.fixture
async def storage_service() -> InMemoryStorageService:
    return InMemoryStorageService()


@pytest_asyncio.fixture
def test_session_factory():
    return TestSessionLocal


@pytest_asyncio.fixture
async def client(db_session: AsyncSession, storage_service: InMemoryStorageService) -> AsyncGenerator[AsyncClient, None]:
    # Chaque requete HTTP obtient sa PROPRE AsyncSession (comme en production).
    # Partager la session de la fixture `db_session` avec l'app aurait cause
    # un acces concurrent a la meme connexion asyncpg, celle-ci s'executant
    # dans une task asyncio distincte via ASGITransport.
    async def override_get_db():
        async with TestSessionLocal() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_storage_service] = lambda: storage_service
    app.dependency_overrides[get_session_factory] = lambda: TestSessionLocal

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


async def _create_user(email: str, password: str, role: UserRole) -> User:
    """Cree (ou met a jour) un utilisateur via une session dediee, independante
    de `db_session`, pour pouvoir etre appelee en toute securite entre deux
    requetes HTTP dans un meme test (chaque requete ouvre aussi sa propre
    session cote app).

    Idempotent par UPDATE (pas delete-then-insert) : un evenement d'un test
    precedent peut encore referencer cet utilisateur (pas de ON DELETE CASCADE
    sur events.organizer_id) si le nettoyage entre tests n'a pas fini de
    s'executer avant que le suivant ne demarre ; un DELETE echouerait alors
    sur une violation de contrainte de cle etrangere."""
    from sqlalchemy import select

    from app.core.security import hash_password

    async with TestSessionLocal() as session:
        existing = (await session.execute(select(User).where(User.email == email))).scalar_one_or_none()
        if existing is not None:
            existing.hashed_password = hash_password(password)
            existing.role = role
            await session.commit()
            await session.refresh(existing)
            return existing

        user = User(email=email, hashed_password=hash_password(password), role=role)
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


@pytest_asyncio.fixture
async def admin_user(setup_test_db) -> User:
    return await _create_user("admin@myface-test.com", "testpassword123", UserRole.ADMIN)


@pytest_asyncio.fixture
def create_user():
    return _create_user


@pytest_asyncio.fixture
async def auth_client(client: AsyncClient, admin_user: User) -> AsyncGenerator[AsyncClient, None]:
    from app.core.security import create_access_token

    token = create_access_token(str(admin_user.id))
    client.headers["Authorization"] = f"Bearer {token}"
    yield client


async def _seed_photo(event_id: str, storage_service, session_factory, filename: str, image_bytes: bytes) -> str:
    """Cree une photo directement en base (sans passer par /photos/upload,
    qui declenche l'indexation faciale automatique en arriere-plan). Utile
    pour les tests panier/paiement qui n'ont pas besoin de vrais visages."""
    import uuid as uuid_module

    from app.models.photo import IndexingStatus, Photo

    photo_id = uuid_module.uuid4()
    original_key = f"events/{event_id}/originals/{photo_id}.jpg"
    thumbnail_key = f"events/{event_id}/thumbnails/{photo_id}.jpg"
    await storage_service.upload(original_key, image_bytes, "image/jpeg")
    await storage_service.upload(thumbnail_key, image_bytes, "image/jpeg")

    async with session_factory() as session:
        photo = Photo(
            id=photo_id,
            event_id=uuid_module.UUID(event_id),
            original_key=original_key,
            thumbnail_key=thumbnail_key,
            original_filename=filename,
            indexing_status=IndexingStatus.DONE,
        )
        session.add(photo)
        await session.commit()

    return str(photo_id)


@pytest_asyncio.fixture
def seed_photo():
    return _seed_photo
