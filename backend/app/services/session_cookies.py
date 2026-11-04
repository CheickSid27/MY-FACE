"""Session des comptes (photographes, admins) dans des cookies proteges.

Les jetons ne sont plus gardes par le site dans le stockage du navigateur
(localStorage), que tout code de la page peut lire : en cas d'injection de
code, la session pouvait etre volee. Les cookies sont HttpOnly (illisibles
par le code de la page), Secure en https et SameSite=Strict (jamais envoyes
par un autre site, ce qui protege aussi des requetes forgees). L'en-tete
« Authorization: Bearer » reste accepte (tests, scripts)."""

from fastapi import Request, Response

from app.core.config import get_settings

settings = get_settings()

ACCESS_COOKIE = "myface_access"
REFRESH_COOKIE = "myface_refresh"


def _secure() -> bool:
    return settings.app_base_url.startswith("https")


def set_session_cookies(response: Response, access_token: str, refresh_token: str | None = None) -> None:
    common = {"httponly": True, "secure": _secure(), "samesite": "strict", "path": "/"}
    response.set_cookie(ACCESS_COOKIE, access_token, max_age=settings.jwt_access_token_expire_minutes * 60, **common)
    if refresh_token is not None:
        response.set_cookie(
            REFRESH_COOKIE, refresh_token, max_age=settings.jwt_refresh_token_expire_days * 86400, **common
        )


def clear_session_cookies(response: Response) -> None:
    for name in (ACCESS_COOKIE, REFRESH_COOKIE):
        response.delete_cookie(name, path="/", secure=_secure(), httponly=True, samesite="strict")


def access_token_from(request: Request) -> str | None:
    """Jeton d'acces : en-tete Authorization, sinon cookie de session."""
    header = request.headers.get("authorization", "")
    if header.lower().startswith("bearer "):
        return header[7:].strip() or None
    return request.cookies.get(ACCESS_COOKIE)
