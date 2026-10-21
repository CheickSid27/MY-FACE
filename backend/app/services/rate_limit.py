"""Limite de debit en memoire (fenetre glissante), pour les routes publiques
sensibles : inscription d'un photographe, mot de passe de galerie.

Un seul processus backend : la memoire du processus suffit (pas de Redis).
L'adresse du visiteur vient de l'en-tete Cloudflare quand il existe (le
tunnel masque sinon l'adresse reelle, voir notes d'architecture)."""

import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request, status


class SlidingWindowLimiter:
    def __init__(self) -> None:
        self._hits: dict[tuple[str, str], deque[float]] = defaultdict(deque)

    def check(self, bucket: str, key: str, limit: int, window_seconds: float) -> None:
        now = time.monotonic()
        hits = self._hits[(bucket, key)]
        while hits and now - hits[0] > window_seconds:
            hits.popleft()
        if len(hits) >= limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Trop de tentatives, reessayez dans quelques minutes",
            )
        hits.append(now)

    def reset(self) -> None:
        self._hits.clear()


limiter = SlidingWindowLimiter()


def client_ip(request: Request) -> str:
    for header in ("cf-connecting-ip", "x-real-ip"):
        value = request.headers.get(header)
        if value:
            return value.strip()
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "inconnu"
