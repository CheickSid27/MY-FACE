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


# --- prix combine photo + tirage (borne) -----------------------------------
DEMO = {
    "unit_price": 450,
    "currency": "XOF",
    "packs": [{"count": 5, "price": 2000}],
    "discounts": [{"min_quantity": 10, "percent": 10}],
    "print_unit_price": 500,
    "print_bundle_price": 700,
}


def test_bundle_price_replaces_photo_plus_print():
    result = calculate_total(DEMO, 1, 1)
    assert result.total == 700
    assert result.subtotal == 0
    assert result.bundle is True


def test_bundle_photos_left_out_of_packs_and_discounts():
    # 10 photos dont 3 imprimees : 7 numeriques seules (1 lot de 5 + 2 a 450,
    # sous le seuil de 10 donc sans remise) + 3 x 700
    result = calculate_total(DEMO, 10, 3)
    assert result.subtotal == 2900
    assert result.discount_percent == 0
    assert result.print_total == 2100
    assert result.total == 5000


def test_discount_still_applies_to_digital_only_photos():
    # 12 photos dont 2 imprimees : 10 numeriques (2 lots = 4000, -10 %) + 2 x 700
    result = calculate_total(DEMO, 12, 2)
    assert result.subtotal == 4000
    assert result.discount_amount == 400
    assert result.total == 3600 + 1400


def test_without_bundle_print_stays_a_supplement():
    pricing = {k: v for k, v in DEMO.items() if k != "print_bundle_price"}
    result = calculate_total(pricing, 1, 1)
    assert result.total == 950
    assert result.bundle is False


def test_item_prices_split_bundle():
    from app.services.pricing import item_prices

    assert item_prices(DEMO, True) == (450.0, 250.0)
    assert item_prices(DEMO, False) == (450.0, None)
