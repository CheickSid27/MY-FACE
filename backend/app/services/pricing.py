"""Calcul du prix d'un panier a partir de la config `Event.pricing` (JSON).

Format attendu :
{
  "unit_price": 1000,
  "currency": "XOF",
  "packs": [{"count": 10, "price": 8000}, ...],   # bundles a prix fixe
  "discounts": [{"min_quantity": 20, "percent": 15}, ...]  # remise degressive
  "print_unit_price": 500,     # tirage papier en plus de la photo (borne)
  "print_bundle_price": 700,   # photo + tirage tout compris (borne)
}

Prix combine (`print_bundle_price`) : chaque photo imprimee coute ce prix,
numerique compris, et sort du calcul des lots et des remises, qui ne portent
que sur les photos seulement numeriques.

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
    # True quand les photos imprimees sont au prix combine (photo + tirage)
    bundle: bool = False


def calculate_total(pricing: dict, photo_count: int, print_count: int = 0) -> PricingBreakdown:
    """`print_count` = nombre de photos, parmi `photo_count`, avec un tirage
    papier demande en plus (voir CartItem.print_requested). Prix fixe par
    tirage (`print_unit_price`), pas de remise de volume dessus pour
    l'instant (a ajouter plus tard si besoin, cf. discussion produit)."""
    currency = pricing.get("currency", "XOF")

    if photo_count <= 0:
        return PricingBreakdown(0, 0.0, 0.0, 0.0, 0, 0.0, 0.0, currency)
    if pricing.get("offert"):
        # photos offertes par l'organisateur : rien a payer, pas de tirage
        return PricingBreakdown(photo_count, 0.0, 0.0, 0.0, 0, 0.0, 0.0, currency)

    bundle_price = float(pricing.get("print_bundle_price") or 0)
    bundle = bundle_price > 0 and print_count > 0
    # avec le prix combine, lots et remises ne portent que sur le numerique seul
    digital_count = photo_count - print_count if bundle else photo_count

    unit_price = float(pricing["unit_price"])
    packs = sorted(
        (p for p in pricing.get("packs", []) if int(p.get("count", 0)) > 0),
        key=lambda p: int(p["count"]),
        reverse=True,
    )

    remaining = digital_count
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
        float(d.get("percent", 0)) for d in discounts if digital_count >= int(d.get("min_quantity", 0))
    ]
    discount_percent = max(applicable_percents, default=0.0)
    discount_amount = subtotal * discount_percent / 100

    print_unit_price = float(pricing.get("print_unit_price") or 0)
    print_total = round(print_count * (bundle_price if bundle else print_unit_price), 2)

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
        bundle=bundle,
    )


def item_prices(pricing: dict, print_requested: bool) -> tuple[float, float | None]:
    """(prix photo, prix tirage) figes dans une ligne de commande. Au prix
    combine, le tirage vaut la difference (700 - 450 = 250) : le recu et les
    totaux d'impression de l'admin restent justes."""
    if pricing.get("offert"):
        return 0.0, None
    unit_price = float(pricing["unit_price"])
    if not print_requested:
        return unit_price, None
    bundle_price = float(pricing.get("print_bundle_price") or 0)
    if bundle_price > 0:
        return unit_price, round(max(0.0, bundle_price - unit_price), 2)
    return unit_price, float(pricing.get("print_unit_price") or 0)
