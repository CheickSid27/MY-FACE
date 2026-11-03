from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db

from app.schemas.meta import MaintenanceStatusRead, PhoneCountryRead
from app.services import maintenance
from app.services import paystack
from app.services.phone import countries_as_dicts
from app.services.sms import sms_delivery_enabled

router = APIRouter(prefix="/meta", tags=["meta"])


@router.get("/phone-countries", response_model=list[PhoneCountryRead])
async def list_phone_countries() -> list[dict]:
    """Indicatifs et formats de numero acceptes a la commande (le premier est
    le pays par defaut). Public : utilise par le panier pour valider la
    saisie avec exactement les memes regles que le serveur."""
    return countries_as_dicts()


@router.get("/features")
async def list_features() -> dict[str, bool]:
    """Ce que l'application peut vraiment faire sur ce serveur, pour que les
    pages n'annoncent rien d'autre (ex : pas de « vous recevrez un SMS » si
    aucun SMS ne peut partir)."""
    return {"sms": sms_delivery_enabled(), "paystack": paystack.is_configured()}


@router.get("/status", response_model=MaintenanceStatusRead)
async def platform_status(db: AsyncSession = Depends(get_db)) -> dict:
    """Mode maintenance, lu par les pages invites a leur chargement. Public."""
    return maintenance.public_view(await maintenance.get_status(db))
