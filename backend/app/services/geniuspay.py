"""Client pour la passerelle de paiement tierce GeniusPay (geniuspay.ci).

Integration ISOLEE, en test sandbox : ne touche pas au flux QR marchand +
confirmation manuelle deja en place (services/payments.py, EventPaymentMethod).
GeniusPay unifie Wave/Orange Money/MTN Money/Moov Money derriere une seule API
avec confirmation automatique par webhook, contrairement au flux manuel actuel
qui exige que l'organisateur valide chaque commande a la main.

Limites connues (voir CGU GeniusPay) a garder en tete :
- GeniusPay se decrit comme un simple intermediaire technique, pas un
  etablissement de paiement/PSP agree ; leur responsabilite contractuelle en
  cas de probleme est plafonnee aux frais payes sur 12 mois, pas aux montants
  de transaction perdus.
- Aucune garantie de disponibilite contractuelle (obligation de moyens).
Ces limites justifient de garder le flux QR existant en parallele tant que
GeniusPay n'a pas fait ses preuves sur des transactions reelles.
"""

import hashlib
import hmac
import json
import time
from dataclasses import dataclass

import httpx

from app.core.config import get_settings

settings = get_settings()


class GeniusPayError(Exception):
    pass


@dataclass
class GeniusPayPaymentResult:
    reference: str
    checkout_url: str
    status: str
    environment: str


def _headers() -> dict[str, str]:
    return {
        "X-API-Key": settings.geniuspay_api_key,
        "X-API-Secret": settings.geniuspay_api_secret,
        "Content-Type": "application/json",
    }


async def init_payment(
    amount: float,
    description: str,
    contact_phone: str,
    order_id: str,
    success_url: str,
    error_url: str,
) -> GeniusPayPaymentResult:
    """Cree une transaction GeniusPay et renvoie l'URL de checkout hebergee.

    `payment_method` est volontairement omis : le client choisit lui-meme
    Wave/Orange/MTN/Moov/carte sur la page de paiement GeniusPay, comme
    recommande par leur documentation pour maximiser le taux de conversion.
    """
    if not settings.geniuspay_api_key or not settings.geniuspay_api_secret:
        raise GeniusPayError(
            "GENIUSPAY_API_KEY / GENIUSPAY_API_SECRET non configures. "
            "Inscrivez-vous sur geniuspay.ci et renseignez vos cles sandbox dans .env."
        )

    payload = {
        "amount": int(amount),
        "currency": "XOF",
        "description": description[:500],
        "customer": {"phone": contact_phone},
        "metadata": {"order_id": order_id},
        "success_url": success_url,
        "error_url": error_url,
    }

    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            resp = await client.post(
                f"{settings.geniuspay_base_url}/payments", json=payload, headers=_headers()
            )
        except httpx.HTTPError as exc:
            raise GeniusPayError(f"GeniusPay injoignable : {exc}") from exc

    body = resp.json()
    if resp.status_code >= 400 or not body.get("success"):
        error = body.get("error", {})
        raise GeniusPayError(
            f"GeniusPay a refuse le paiement ({error.get('code', resp.status_code)}) : "
            f"{error.get('message', resp.text)}"
        )

    data = body["data"]
    return GeniusPayPaymentResult(
        reference=data["reference"],
        checkout_url=data.get("checkout_url") or data["payment_url"],
        # Constate en sandbox (voir test manuel) : "status" peut etre `null`
        # dans la reponse de creation, contrairement a l'exemple de la doc
        # ("pending"). On retombe sur "pending" (etat reel a la creation :
        # rien n'a encore ete paye) plutot que de planter la validation.
        status=data.get("status") or "pending",
        environment=data["environment"],
    )


def verify_webhook_signature(raw_body: bytes, signature: str | None, timestamp: str | None) -> bool:
    """HMAC-SHA256(timestamp + "." + payload, secret webhook), + fenetre
    anti-rejeu de 5 minutes, exactement le schema documente par GeniusPay."""
    if not signature or not timestamp or not settings.geniuspay_webhook_secret:
        return False

    try:
        if abs(time.time() - int(timestamp)) > 300:
            return False
    except ValueError:
        return False

    # Le payload doit etre re-serialise a l'identique de ce que GeniusPay a
    # signe cote serveur (json.dumps sans espace ajoute apres les separateurs,
    # cle d'ordre stable) : on verifie donc sur les bytes bruts recus, pas sur
    # une reserialisation Python qui pourrait differer (ordre des cles,
    # espaces). Voir le point d'appel dans routers/geniuspay.py.
    to_sign = f"{timestamp}.{raw_body.decode('utf-8')}".encode("utf-8")
    expected = hmac.new(settings.geniuspay_webhook_secret.encode("utf-8"), to_sign, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


def parse_event(raw_body: bytes) -> dict:
    return json.loads(raw_body)
