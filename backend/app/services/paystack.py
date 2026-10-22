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
from app.models.user import User, UserRole


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


def online_payment_available(owner: User | None) -> bool:
    """Paiement en ligne des photos par les invites : uniquement pour les
    evenements de MYFACE (organisateur admin). Pour ceux d'un photographe,
    l'argent lui revient : il reste paye directement sur son Wave ou son
    Orange Money (partage automatique a prevoir avec un compte enregistre)."""
    return is_configured() and owner is not None and owner.role == UserRole.ADMIN


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


async def settle_order(order, db) -> None:
    """Commande de photos payee en ligne : redemande l'etat a Paystack et la
    passe payee (SMS, telechargement) si le paiement est reussi, au bon
    montant, en francs CFA. Une commande annulee faute de paiement dans le
    delai est quand meme validee si l'argent est finalement arrive."""
    from app.models.order import OrderStatus, PaymentMethod
    from app.services.orders import set_order_status

    if order.payment_method != PaymentMethod.PAYSTACK or order.status not in (
        OrderStatus.PENDING,
        OrderStatus.CANCELLED,
    ):
        return
    tx = await verify_transaction(order.payment_reference)
    if tx.status == "success" and tx.currency == "XOF" and tx.amount >= int(order.total_amount):
        await set_order_status(order, OrderStatus.SUCCESS, db)
        await _notify_sale(order, db)
    elif tx.status in ("failed", "reversed") and order.status == OrderStatus.PENDING:
        await set_order_status(order, OrderStatus.FAILED, db)


async def _notify_sale(order, db) -> None:
    """Notification a l'organisateur pour chaque vente payee en ligne."""
    from app.models.event import Event
    from app.services.push_notifications import send_push_to_user

    event = await db.get(Event, order.event_id)
    if event is None:
        return
    amount = f"{order.total_amount:,.0f}".replace(",", " ")
    await send_push_to_user(
        event.organizer_id,
        db,
        title=f"Nouvelle vente : {amount} F",
        body=f"Payée en ligne, {event.name}. Les photos sont déjà envoyées à l'invité.",
        url=f"/admin/events/{event.id}?onglet=ventes",
        tag=f"commande-{order.id}",
    )
