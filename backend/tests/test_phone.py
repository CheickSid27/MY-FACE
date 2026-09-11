import re

import pytest

from app.services.phone import COUNTRIES, DEFAULT_COUNTRY_ISO, normalize_phone


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("+2250701020304", "+2250701020304"),
        ("+225 07 01 02 03 04", "+2250701020304"),
        ("00225-05.01.02.03.04", "+2250501020304"),
        ("+225 01 01 02 03 04", "+2250101020304"),
        ("+221 77 123 45 67", "+221771234567"),
        ("+33 6 12 34 56 78", "+33612345678"),
        # Prefixe national 0 saisi par habitude : retire (France, Ghana).
        ("+33 06 12 34 56 78", "+33612345678"),
        ("+233 024 123 4567", "+233241234567"),
        ("+229 01 90 12 34 56", "+2290190123456"),
        ("+1 201 555 0123", "+12015550123"),
    ],
)
def test_normalize_valid_numbers(raw, expected):
    assert normalize_phone(raw) == expected


@pytest.mark.parametrize(
    "raw",
    [
        "",
        "0701020304",  # indicatif manquant
        "+225 0701020",  # trop court
        "+225 09 01 02 03 04",  # prefixe non mobile en Cote d'Ivoire
        "+225 21 21 21 21 21",  # fixe : pas de SMS possible
        "+221 33 123 45 67",  # Senegal : fixe
        "+999 12345678",  # indicatif inconnu
        "+225 07 01 02 03 0a",
    ],
)
def test_normalize_rejects_invalid_numbers(raw):
    with pytest.raises(ValueError):
        normalize_phone(raw)


def test_error_message_explains_expected_format():
    with pytest.raises(ValueError, match="10 chiffres commencant par 01, 05 ou 07"):
        normalize_phone("+225 12 34 56 78")


def test_country_table_is_consistent():
    assert COUNTRIES[0].iso == DEFAULT_COUNTRY_ISO
    assert len({c.dial_code for c in COUNTRIES}) == len(COUNTRIES)
    for country in COUNTRIES:
        # L'exemple affiche au client doit lui-meme etre valide.
        assert re.fullmatch(country.pattern, country.example), country.iso
        assert normalize_phone(f"+{country.dial_code}{country.example}") == f"+{country.dial_code}{country.example}"
