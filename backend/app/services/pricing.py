"""Calcul du prix d'un panier a partir de la config `Event.pricing` (JSON).

Format attendu :
{
  "unit_price": 1000,
  "currency": "XOF",
  "packs": [{"count": 10, "price": 8000}, ...],   # bundles a prix fixe
  "discounts": [{"min_quantity": 20, "percent": 15}, ...]  # remise degressive
}

Algorithme : on applique greedily les packs les plus grands en premier sur le
nombre de photos, le reste au prix unitaire, puis on applique la meilleure
remise de volume (percent) applicable au sous-total obtenu.
"""

from dataclasses import dataclass


@dataclass
class PricingBreakdown:
    photo_count: int
    subtotal: float
    discount_percent: float
    discount_amount: float
    print_count: int
    print_total: float
    total: float
    currency: str


def calculate_total(pricing: dict, photo_count: int, print_count: int = 0) -> PricingBreakdown:
    """`print_count` = nombre de photos, parmi `photo_count`, avec un tirage
    papier demande en plus (voir CartItem.print_requested). Prix fixe par
    tirage (`print_unit_price`), pas de remise de volume dessus pour
    l'instant (a ajouter plus tard si besoin, cf. discussion produit)."""
    currency = pricing.get("currency", "XOF")

    if photo_count <= 0:
        return PricingBreakdown(0, 0.0, 0.0, 0.0, 0, 0.0, 0.0, currency)

    unit_price = float(pricing["unit_price"])
    packs = sorted(
        (p for p in pricing.get("packs", []) if int(p.get("count", 0)) > 0),
        key=lambda p: int(p["count"]),
        reverse=True,
    )

    remaining = photo_count
    subtotal = 0.0
    for pack in packs:
        count = int(pack["count"])
        price = float(pack["price"])
        bundles = remaining // count
        if bundles > 0:
            subtotal += bundles * price
            remaining -= bundles * count
    subtotal += remaining * unit_price

    discounts = pricing.get("discounts", [])
    applicable_percents = [
        float(d.get("percent", 0)) for d in discounts if photo_count >= int(d.get("min_quantity", 0))
    ]
    discount_percent = max(applicable_percents, default=0.0)
    discount_amount = subtotal * discount_percent / 100

    print_unit_price = float(pricing.get("print_unit_price") or 0)
    print_total = round(print_count * print_unit_price, 2)

    total = round(subtotal - discount_amount + print_total, 2)

    return PricingBreakdown(
        photo_count=photo_count,
        subtotal=round(subtotal, 2),
        discount_percent=discount_percent,
        discount_amount=round(discount_amount, 2),
        print_count=print_count,
        print_total=print_total,
        total=total,
        currency=currency,
    )
