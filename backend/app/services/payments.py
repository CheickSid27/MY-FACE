"""Adaptateurs de paiement Mobile Money.

IMPORTANT (section 0 du cahier des charges) : aucun des adaptateurs reels
(Wave, Orange Money, MTN Money, Moov Money) n'est fonctionnel actuellement.
Nous n'avons ni credentials marchand, ni acces verifie a leurs API. Plutot
que de deviner des endpoints/format de payload (ce qui produirait un code
qui a l'air de marcher mais echouerait silencieusement ou de facon
imprevisible en prod), chaque adaptateur reel leve NotImplementedError avec
un message explicite tant qu'il n'est pas branche avec de vraies cles et
implemente contre la documentation officielle de l'operateur.

L'adaptateur MANUAL est un simulateur de dev/test explicitement signale comme
tel : il ne deplace jamais d'argent reel. Il permet de tester tout le
parcours (panier -> paiement -> telechargement) avant que les vrais
operateurs soient integres. Le provider actif est choisi par
PAYMENT_PROVIDER dans .env — jamais de fallback silencieux vers MANUAL si un
autre provider est demande sans etre configure : dans ce cas on leve une
erreur claire.
"""

import hashlib
import hmac
import secrets
from abc import ABC, abstractmethod
from dataclasses import dataclass
from functools import lru_cache

from app.core.config import get_settings
from app.models.order import Order

settings = get_settings()


@dataclass
class PaymentInitResult:
    reference: str
    redirect_url: str | None = None
    instructions: str | None = None


class PaymentProvider(ABC):
    @abstractmethod
    async def init_payment(self, order: Order) -> PaymentInitResult:
        """Demarre le paiement cote operateur, retourne une reference a suivre."""

    @abstractmethod
    def verify_webhook_signature(self, raw_body: bytes, signature: str | None) -> bool:
        """Verifie la signature HMAC du webhook entrant."""


def _hmac_sign(secret: str, raw_body: bytes) -> str:
    return hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()


class ManualPaymentAdapter(PaymentProvider):
    """Simulateur de paiement pour le dev/test. AUCUN ARGENT REEL NE BOUGE.

    Le paiement est initie avec une reference locale ; sa confirmation se
    fait via l'endpoint de test `POST /payments/{order_id}/simulate` (non
    expose en production, voir routers/payments.py), qui reproduit le meme
    chemin de code qu'un vrai webhook operateur (signature HMAC comprise)."""

    async def init_payment(self, order: Order) -> PaymentInitResult:
        reference = f"MANUAL-{secrets.token_hex(8)}"
        return PaymentInitResult(
            reference=reference,
            instructions="Mode test (aucun paiement reel) : confirmez via l'endpoint de simulation.",
        )

    def verify_webhook_signature(self, raw_body: bytes, signature: str | None) -> bool:
        if signature is None:
            return False
        return hmac.compare_digest(signature, _hmac_sign(settings.payment_webhook_secret, raw_body))


class WaveAdapter(PaymentProvider):
    def __init__(self) -> None:
        if not settings.wave_api_key:
            raise NotImplementedError(
                "PAYMENT_PROVIDER=wave mais WAVE_API_KEY n'est pas configure. "
                "Fournissez cette cle dans .env, ou utilisez PAYMENT_PROVIDER=manual en attendant. "
                "L'integration Wave (checkout API) reste a implementer contre la documentation "
                "officielle une fois les credentials disponibles."
            )

    async def init_payment(self, order: Order) -> PaymentInitResult:  # pragma: no cover
        raise NotImplementedError("Integration Wave non implementee.")

    def verify_webhook_signature(self, raw_body: bytes, signature: str | None) -> bool:  # pragma: no cover
        raise NotImplementedError("Integration Wave non implementee.")


class OrangeMoneyAdapter(PaymentProvider):
    def __init__(self) -> None:
        if not settings.orange_money_api_key or not settings.orange_money_merchant_id:
            raise NotImplementedError(
                "PAYMENT_PROVIDER=orange_money mais ORANGE_MONEY_API_KEY / "
                "ORANGE_MONEY_MERCHANT_ID ne sont pas configures. Fournissez ces cles dans "
                ".env, ou utilisez PAYMENT_PROVIDER=manual en attendant. L'integration Orange "
                "Money Web Payment reste a implementer contre la documentation officielle."
            )

    async def init_payment(self, order: Order) -> PaymentInitResult:  # pragma: no cover
        raise NotImplementedError("Integration Orange Money non implementee.")

    def verify_webhook_signature(self, raw_body: bytes, signature: str | None) -> bool:  # pragma: no cover
        raise NotImplementedError("Integration Orange Money non implementee.")


class MTNMoneyAdapter(PaymentProvider):
    def __init__(self) -> None:
        if not settings.mtn_money_api_key or not settings.mtn_money_subscription_key:
            raise NotImplementedError(
                "PAYMENT_PROVIDER=mtn_money mais MTN_MONEY_API_KEY / "
                "MTN_MONEY_SUBSCRIPTION_KEY ne sont pas configures. Fournissez ces cles dans "
                ".env, ou utilisez PAYMENT_PROVIDER=manual en attendant. L'integration MTN "
                "MoMo API reste a implementer contre la documentation officielle."
            )

    async def init_payment(self, order: Order) -> PaymentInitResult:  # pragma: no cover
        raise NotImplementedError("Integration MTN Money non implementee.")

    def verify_webhook_signature(self, raw_body: bytes, signature: str | None) -> bool:  # pragma: no cover
        raise NotImplementedError("Integration MTN Money non implementee.")


class MoovMoneyAdapter(PaymentProvider):
    def __init__(self) -> None:
        if not settings.moov_money_api_key:
            raise NotImplementedError(
                "PAYMENT_PROVIDER=moov_money mais MOOV_MONEY_API_KEY n'est pas configure. "
                "Fournissez cette cle dans .env, ou utilisez PAYMENT_PROVIDER=manual en attendant. "
                "L'integration Moov Money reste a implementer contre la documentation officielle."
            )

    async def init_payment(self, order: Order) -> PaymentInitResult:  # pragma: no cover
        raise NotImplementedError("Integration Moov Money non implementee.")

    def verify_webhook_signature(self, raw_body: bytes, signature: str | None) -> bool:  # pragma: no cover
        raise NotImplementedError("Integration Moov Money non implementee.")


_PROVIDERS = {
    "manual": ManualPaymentAdapter,
    "wave": WaveAdapter,
    "orange_money": OrangeMoneyAdapter,
    "mtn_money": MTNMoneyAdapter,
    "moov_money": MoovMoneyAdapter,
}


@lru_cache
def get_payment_provider() -> PaymentProvider:
    provider_cls = _PROVIDERS.get(settings.payment_provider)
    if provider_cls is None:
        raise ValueError(f"PAYMENT_PROVIDER inconnu: {settings.payment_provider!r}")
    return provider_cls()
