from app.services.pricing import calculate_total


def test_zero_photos():
    result = calculate_total({"unit_price": 1000, "currency": "XOF"}, 0)
    assert result.total == 0.0
    assert result.photo_count == 0


def test_unit_price_only():
    result = calculate_total({"unit_price": 1000, "currency": "XOF"}, 3)
    assert result.subtotal == 3000
    assert result.total == 3000
    assert result.discount_percent == 0.0


def test_pack_pricing_applied():
    pricing = {
        "unit_price": 1000,
        "currency": "XOF",
        "packs": [{"count": 10, "price": 8000}],
    }
    result = calculate_total(pricing, 10)
    assert result.subtotal == 8000
    assert result.total == 8000


def test_pack_pricing_with_remainder():
    pricing = {
        "unit_price": 1000,
        "currency": "XOF",
        "packs": [{"count": 10, "price": 8000}],
    }
    result = calculate_total(pricing, 13)
    # 1 pack (8000) + 3 unites (3000)
    assert result.subtotal == 11000


def test_largest_pack_preferred():
    pricing = {
        "unit_price": 1000,
        "currency": "XOF",
        "packs": [{"count": 5, "price": 4500}, {"count": 10, "price": 8000}],
    }
    result = calculate_total(pricing, 10)
    # doit utiliser le pack de 10 (8000) plutot que 2x pack de 5 (9000)
    assert result.subtotal == 8000


def test_volume_discount_applied():
    pricing = {
        "unit_price": 1000,
        "currency": "XOF",
        "discounts": [{"min_quantity": 20, "percent": 15}],
    }
    result = calculate_total(pricing, 20)
    assert result.subtotal == 20000
    assert result.discount_percent == 15
    assert result.discount_amount == 3000
    assert result.total == 17000


def test_discount_not_applied_below_threshold():
    pricing = {
        "unit_price": 1000,
        "currency": "XOF",
        "discounts": [{"min_quantity": 20, "percent": 15}],
    }
    result = calculate_total(pricing, 19)
    assert result.discount_percent == 0.0
    assert result.total == 19000


def test_best_discount_tier_used():
    pricing = {
        "unit_price": 1000,
        "currency": "XOF",
        "discounts": [
            {"min_quantity": 10, "percent": 5},
            {"min_quantity": 20, "percent": 15},
        ],
    }
    result = calculate_total(pricing, 25)
    assert result.discount_percent == 15
