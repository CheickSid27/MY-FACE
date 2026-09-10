from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.routers import admin, auth, cart, download, events, faces, geniuspay, notifications, payments, photos
from app.services.face_recognition import preload_face_analysis
from app.services.folder_watcher import folder_watcher

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await preload_face_analysis()
    folder_watcher.start()
    yield
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


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
