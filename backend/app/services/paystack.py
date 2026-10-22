"""Client Paystack (paystack.com) pour le paiement des packs photographes.

Parcours : le serveur cree une transaction (initialize) et renvoie le lien
de la page Paystack (Wave, Orange Money, MTN, carte) ; une fois paye,
Paystack previent le serveur (webhook signe en HMAC-SHA512 avec la cle
secrete) et renvoie le photographe sur l'application. Dans les deux cas on
redemande a Paystack l'etat reel de la transaction (verify) avant
d'activer quoi que ce soit : ni la redirection ni le webhook seuls ne font
foi.

Montants : Paystack les attend en centiemes, y compris pour le franc CFA
(1 000 000 = 10 000 F, verifie le 22/10 sur la page de paiement de test).
"""

import hashlib
import hmac
from dataclasses import dataclass

import httpx

from app.core.config import get_settings


class PaystackError(Exception):
    pass


@dataclass
class PaystackTransaction:
    reference: str
    status: str  # success, failed, abandoned, ongoing, pending...
    amount: int  # en francs, deja divise par 100
    currency: str


def is_configured() -> bool:
    return bool(get_settings().paystack_secret_key)


def _headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {get_settings().paystack_secret_key}",
        "Content-Type": "application/json",
    }


async def initialize_transaction(
    email: str, amount: int, reference: str, callback_url: str, metadata: dict
) -> str:
    """Cree la transaction et renvoie le lien de la page de paiement."""
    settings = get_settings()
    payload = {
        "email": email,
        "amount": amount * 100,
        "currency": "XOF",
        "reference": reference,
        "callback_url": callback_url,
        "channels": ["mobile_money", "card"],
        "metadata": metadata,
    }
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.post(
            f"{settings.paystack_base_url}/transaction/initialize", json=payload, headers=_headers()
        )
    data = response.json() if response.content else {}
    if response.status_code != 200 or not data.get("status"):
        raise PaystackError(data.get("message") or f"Paystack a repondu {response.status_code}")
    return data["data"]["authorization_url"]


async def verify_transaction(reference: str) -> PaystackTransaction:
    settings = get_settings()
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.get(
            f"{settings.paystack_base_url}/transaction/verify/{reference}", headers=_headers()
        )
    data = response.json() if response.content else {}
    if response.status_code != 200 or not data.get("status"):
        raise PaystackError(data.get("message") or f"Paystack a repondu {response.status_code}")
    tx = data["data"]
    return PaystackTransaction(
        reference=tx["reference"],
        status=tx.get("status") or "",
        amount=int(tx.get("amount") or 0) // 100,
        currency=tx.get("currency") or "",
    )


def signature_is_valid(raw_body: bytes, signature: str | None) -> bool:
    secret = get_settings().paystack_secret_key
    if not secret or not signature:
        return False
    expected = hmac.new(secret.encode(), raw_body, hashlib.sha512).hexdigest()
    return hmac.compare_digest(expected, signature)
