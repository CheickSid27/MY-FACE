"""Journal des requetes lisible : une ligne par requete, avec sa duree.

    [myface.requetes] GET /events/{id}/photos 200 en 84 ms
    [myface.requetes] LENT POST /photos/upload 201 en 9 214 ms (seuil 2 000 ms)

Les identifiants (UUID, codes) sont remplaces par {id} pour que les lignes se
regroupent : l'agent de surveillance et un humain voient tout de suite quelle
route est lente. Les sondes de sante et de statut ne sont pas notees (bruit).
Chaque reponse porte aussi l'en-tete Server-Timing (duree serveur), lisible
dans l'onglet Reseau du navigateur."""

import logging
import re
import time

from starlette.types import ASGIApp, Message, Receive, Scope, Send

logger = logging.getLogger("myface.requetes")

SLOW_MS = 2000
_SKIP = {"/health", "/meta/status"}
_ID = re.compile(r"/[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}|/[A-Z0-9]{8,}(?=/|$)")


def route_label(path: str) -> str:
    return _ID.sub("/{id}", path)


class RequestLogMiddleware:
    """Middleware ASGI pur (ne bufferise pas les reponses, compatible avec les envois de fichiers)."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope["path"] in _SKIP:
            await self.app(scope, receive, send)
            return
        start = time.perf_counter()
        status = 500

        async def send_wrapper(message: Message) -> None:
            nonlocal status
            if message["type"] == "http.response.start":
                status = message["status"]
                elapsed = (time.perf_counter() - start) * 1000
                headers = list(message.get("headers", []))
                headers.append((b"server-timing", f"app;dur={elapsed:.0f}".encode()))
                message["headers"] = headers
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            ms = (time.perf_counter() - start) * 1000
            label = f"{scope['method']} {route_label(scope['path'])} {status} en {ms:,.0f} ms".replace(",", " ")
            if ms >= SLOW_MS:
                logger.warning("LENT %s (seuil %s ms)", label, f"{SLOW_MS:,}".replace(",", " "))
            elif status >= 500:
                logger.error("ERREUR %s", label)
            else:
                logger.info("%s", label)
