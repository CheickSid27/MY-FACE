"""Validation et normalisation des numeros de telephone clients.

Le numero saisi a la commande sert a envoyer le SMS de confirmation (lien
de telechargement) et a identifier la commande cote organisateur. Il etait
accepte tel quel (vus en base : "1123456", "12345678"...), donc souvent
inutilisable. Desormais :
- le client choisit l'indicatif pays (Cote d'Ivoire par defaut) ;
- le numero national doit respecter le format reel du pays (longueur et
  prefixes mobiles) ;
- il est stocke au format international E.164 ("+2250701020304"), celui
  qu'attend Africa's Talking pour l'envoi de SMS.

La meme table est exposee au frontend (GET /meta/phone-countries) pour
valider pendant la saisie, avec exactement les memes regles.

`pattern` s'applique au numero national (sans indicatif). `trunk_prefix` :
prefixe national a retirer s'il est saisi (ex: France "06 12..." ->
"+33 6 12..."). En Cote d'Ivoire (depuis 2021) et au Benin (depuis 2024), le
0 initial fait partie du numero et n'est jamais retire."""

import re
from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class PhoneCountry:
    iso: str
    name: str
    dial_code: str
    pattern: str
    example: str
    hint: str
    trunk_prefix: str | None = None


# Cote d'Ivoire en tete (pays par defaut), puis Afrique de l'Ouest/centrale,
# Maghreb, puis diaspora.
COUNTRIES: tuple[PhoneCountry, ...] = (
    PhoneCountry("CI", "Cote d'Ivoire", "225", r"0[157]\d{8}", "0701020304",
                 "10 chiffres commencant par 01, 05 ou 07"),
    PhoneCountry("SN", "Senegal", "221", r"7[05678]\d{7}", "771234567",
                 "9 chiffres commencant par 70, 75, 76, 77 ou 78"),
    PhoneCountry("ML", "Mali", "223", r"[5-9]\d{7}", "76123456",
                 "8 chiffres commencant par 5, 6, 7, 8 ou 9"),
    PhoneCountry("BF", "Burkina Faso", "226", r"[04-7]\d{7}", "70123456",
                 "8 chiffres commencant par 0, 4, 5, 6 ou 7"),
    PhoneCountry("GN", "Guinee", "224", r"6\d{8}", "621234567",
                 "9 chiffres commencant par 6"),
    PhoneCountry("TG", "Togo", "228", r"[79]\d{7}", "90123456",
                 "8 chiffres commencant par 7 ou 9"),
    PhoneCountry("BJ", "Benin", "229", r"01\d{8}", "0190123456",
                 "10 chiffres commencant par 01"),
    PhoneCountry("NE", "Niger", "227", r"[89]\d{7}", "90123456",
                 "8 chiffres commencant par 8 ou 9"),
    PhoneCountry("GH", "Ghana", "233", r"[25]\d{8}", "241234567",
                 "9 chiffres commencant par 2 ou 5 (sans le 0 initial)", "0"),
    PhoneCountry("NG", "Nigeria", "234", r"[789][01]\d{8}", "8031234567",
                 "10 chiffres commencant par 70, 80, 81, 90 ou 91 (sans le 0 initial)", "0"),
    PhoneCountry("CM", "Cameroun", "237", r"6\d{8}", "671234567",
                 "9 chiffres commencant par 6"),
    PhoneCountry("CG", "Congo", "242", r"0[456]\d{7}", "061234567",
                 "9 chiffres commencant par 04, 05 ou 06"),
    PhoneCountry("CD", "RD Congo", "243", r"[89]\d{8}", "812345678",
                 "9 chiffres commencant par 8 ou 9 (sans le 0 initial)", "0"),
    PhoneCountry("MA", "Maroc", "212", r"[67]\d{8}", "612345678",
                 "9 chiffres commencant par 6 ou 7 (sans le 0 initial)", "0"),
    PhoneCountry("DZ", "Algerie", "213", r"[567]\d{8}", "551234567",
                 "9 chiffres commencant par 5, 6 ou 7 (sans le 0 initial)", "0"),
    PhoneCountry("TN", "Tunisie", "216", r"[2459]\d{7}", "20123456",
                 "8 chiffres commencant par 2, 4, 5 ou 9"),
    PhoneCountry("LB", "Liban", "961", r"(?:3\d{6}|7[01689]\d{6}|81\d{6})", "71123456",
                 "7 ou 8 chiffres commencant par 3, 7 ou 81 (sans le 0 initial)", "0"),
    PhoneCountry("FR", "France", "33", r"[67]\d{8}", "612345678",
                 "9 chiffres commencant par 6 ou 7 (sans le 0 initial)", "0"),
    PhoneCountry("BE", "Belgique", "32", r"4[5-9]\d{7}", "470123456",
                 "9 chiffres commencant par 45 a 49 (sans le 0 initial)", "0"),
    PhoneCountry("CH", "Suisse", "41", r"7[5-9]\d{7}", "781234567",
                 "9 chiffres commencant par 75 a 79 (sans le 0 initial)", "0"),
    PhoneCountry("GB", "Royaume-Uni", "44", r"7\d{9}", "7400123456",
                 "10 chiffres commencant par 7 (sans le 0 initial)", "0"),
    PhoneCountry("ES", "Espagne", "34", r"[67]\d{8}", "612345678",
                 "9 chiffres commencant par 6 ou 7"),
    PhoneCountry("IT", "Italie", "39", r"3\d{8,9}", "3123456789",
                 "9 ou 10 chiffres commencant par 3"),
    PhoneCountry("DE", "Allemagne", "49", r"1[5-7]\d{8,9}", "15123456789",
                 "10 ou 11 chiffres commencant par 15, 16 ou 17 (sans le 0 initial)", "0"),
    PhoneCountry("US", "Etats-Unis / Canada", "1", r"[2-9]\d{2}[2-9]\d{6}", "2015550123",
                 "10 chiffres (indicatif regional + numero)", "1"),
)

DEFAULT_COUNTRY_ISO = "CI"

_BY_DIAL_CODE: dict[str, PhoneCountry] = {c.dial_code: c for c in COUNTRIES}
_MAX_DIAL_CODE_LEN = max(len(c.dial_code) for c in COUNTRIES)
_SEPARATORS = re.compile(r"[\s.\-()/]")


def _match_country(digits: str) -> PhoneCountry | None:
    # Indicatifs sans ambiguite de prefixe dans la table : le plus long qui
    # correspond l'emporte (ex: "225" avant un hypothetique "22").
    for length in range(_MAX_DIAL_CODE_LEN, 0, -1):
        country = _BY_DIAL_CODE.get(digits[:length])
        if country is not None:
            return country
    return None


def normalize_phone(raw: str) -> str:
    """Valide un numero international ("+225 07 01 02 03 04", "00225...")
    et le renvoie au format E.164 ("+2250701020304").

    Leve ValueError avec un message explicite en francais sinon."""
    compact = _SEPARATORS.sub("", raw or "")
    if compact.startswith("00"):
        compact = "+" + compact[2:]
    if not compact.startswith("+") or not compact[1:].isdigit():
        raise ValueError("Numero de telephone invalide : choisissez le pays puis saisissez le numero")

    digits = compact[1:]
    country = _match_country(digits)
    if country is None:
        raise ValueError("Indicatif pays non pris en charge")

    national = digits[len(country.dial_code):]
    if (
        country.trunk_prefix
        and not re.fullmatch(country.pattern, national)
        and national.startswith(country.trunk_prefix)
    ):
        national = national[len(country.trunk_prefix):]

    if not re.fullmatch(country.pattern, national):
        raise ValueError(f"Numero invalide pour {country.name} (+{country.dial_code}) : {country.hint}")
    return f"+{country.dial_code}{national}"


def countries_as_dicts() -> list[dict]:
    return [asdict(country) for country in COUNTRIES]
