"""Limite de debit en memoire (fenetre glissante), pour les routes publiques
sensibles : connexion, inscription, liens envoyes par e-mail, mot de passe
de galerie.

Un seul processus backend : la memoire du processus suffit (pas de Redis).
L'adresse du visiteur vient de l'en-tete Cloudflare quand il existe (le
tunnel masque sinon l'adresse reelle, voir notes d'architecture)."""

import time
from collections import deque

from fastapi import HTTPException, Request, status

# Au-dela, les compteurs vides ou perimes sont retires (sinon des milliers
# d'adresses ou d'e-mails differents feraient grossir la memoire sans fin).
_SWEEP_ABOVE = 10_000
# Plus longue fenetre utilisee par les routes (1 heure).
_MAX_WINDOW_SECONDS = 3600


class SlidingWindowLimiter:
    def __init__(self) -> None:
        self._hits: dict[tuple[str, str], deque[float]] = {}

    def _recent(self, bucket: str, key: str, window_seconds: float) -> deque[float]:
        now = time.monotonic()
        hits = self._hits.setdefault((bucket, key), deque())
        while hits and now - hits[0] > window_seconds:
            hits.popleft()
        return hits

    def _sweep(self) -> None:
        now = time.monotonic()
        stale = [k for k, hits in self._hits.items() if not hits or now - hits[-1] > _MAX_WINDOW_SECONDS]
        for k in stale:
            del self._hits[k]

    def check(self, bucket: str, key: str, limit: int, window_seconds: float, record: bool = True) -> None:
        """Refuse (429) au-dela de `limit` passages dans la fenetre. Avec
        record=False, verifie sans compter : l'appelant compte lui-meme avec
        `hit` (connexion : seuls les mauvais mots de passe comptent)."""
        if len(self._hits) > _SWEEP_ABOVE:
            self._sweep()
        hits = self._recent(bucket, key, window_seconds)
        if len(hits) >= limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Trop de tentatives, réessayez dans quelques minutes",
            )
        if record:
            hits.append(time.monotonic())

    def hit(self, bucket: str, key: str) -> None:
        self._hits.setdefault((bucket, key), deque()).append(time.monotonic())

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
