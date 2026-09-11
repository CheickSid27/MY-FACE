from fastapi import APIRouter

from app.schemas.meta import PhoneCountryRead
from app.services.phone import countries_as_dicts

router = APIRouter(prefix="/meta", tags=["meta"])


@router.get("/phone-countries", response_model=list[PhoneCountryRead])
async def list_phone_countries() -> list[dict]:
    """Indicatifs et formats de numero acceptes a la commande (le premier est
    le pays par defaut). Public : utilise par le panier pour valider la
    saisie avec exactement les memes regles que le serveur."""
    return countries_as_dicts()
