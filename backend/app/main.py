import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.database import AsyncSessionLocal
from app.routers import (
    admin,
    auth,
    cart,
    download,
    events,
    faces,
    geniuspay,
    meta,
    notifications,
    payments,
    photos,
)
from app.services.face_clusters import face_cluster_cache, recent_event_ids
from app.services.face_indexing import recover_unfinished_indexing
from app.services.face_recognition import preload_face_analysis
from app.services.folder_watcher import folder_watcher
from app.services.orders import run_startup_maintenance
from app.services.storage import get_storage_service
from app.services.watermark import backfill_watermarks

settings = get_settings()

# Logs applicatifs ("myface.*") : uvicorn ne configure que ses propres
# loggers, les messages INFO de l'app (indexation, dossier surveille,
# rattrapages au demarrage) etaient donc invisibles dans `docker logs`.
_app_logger = logging.getLogger("myface")
if not _app_logger.handlers:
    _handler = logging.StreamHandler()
    _handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s [%(name)s] %(message)s"))
    _app_logger.addHandler(_handler)
    _app_logger.setLevel(logging.INFO)
    _app_logger.propagate = False

logger = logging.getLogger("myface.startup")


async def _startup_jobs() -> None:
    """Rattrapages lances en arriere-plan au demarrage, sans retarder la
    disponibilite de l'API : annulation des commandes jamais payees, reprise
    des indexations interrompues, filigrane des anciennes photos, puis
    pre-calcul des groupes de visages des evenements recents."""
    await run_startup_maintenance(AsyncSessionLocal)
    try:
        storage = get_storage_service()
        await recover_unfinished_indexing(storage, AsyncSessionLocal)
        await backfill_watermarks(storage, AsyncSessionLocal, on_event_updated=face_cluster_cache.invalidate)
        async with AsyncSessionLocal() as db:
            event_ids = await recent_event_ids(db)
        await face_cluster_cache.prewarm(event_ids, storage, AsyncSessionLocal)
    except Exception:
        logger.exception("Rattrapages au demarrage : echec")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await preload_face_analysis()
    folder_watcher.start()
    startup_task = asyncio.create_task(_startup_jobs())
    yield
    startup_task.cancel()
    await folder_watcher.stop()


app = FastAPI(title="MYFACE API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(events.router)
app.include_router(photos.router)
app.include_router(faces.router)
app.include_router(cart.router)
app.include_router(payments.router)
app.include_router(download.router)
app.include_router(admin.router)
app.include_router(notifications.router)
app.include_router(geniuspay.router)
app.include_router(meta.router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
