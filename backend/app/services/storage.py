"""Abstraction de stockage fichiers.

Deux implementations :
- LocalS3StorageService : S3-compatible (MinIO en local, Cloudflare R2 en ligne).
- SupabaseStorageService : necessite SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY.
  NON BRANCHE tant que les credentials Supabase ne sont pas fournis par
  l'utilisateur -> leve NotImplementedError avec message explicite si utilisee
  sans configuration, pour ne jamais livrer de comportement mock silencieux.

Le bucket est PRIVE : aucun objet (miniature ou original) n'est accessible
directement par URL statique. Toute lecture passe par une URL signee a
expiration courte, generee a la demande via `get_presigned_url`. C'est ce qui
permet de reserver l'acces aux photos originales aux commandes payees
(section 8 du cahier des charges : "URLs de telechargement signees, a
expiration courte").
"""

import asyncio
import time
from abc import ABC, abstractmethod
from functools import lru_cache
from urllib.parse import quote, urlencode

import boto3
from botocore.auth import S3SigV4QueryAuth
from botocore.awsrequest import AWSRequest
from botocore.client import Config as BotoConfig
from botocore.credentials import Credentials
from botocore.exceptions import ClientError

from app.core.config import get_settings

settings = get_settings()

# delete_objects S3 accepte au maximum 1000 cles par requete.
_S3_DELETE_BATCH = 1000


def content_disposition_attachment(filename: str) -> str:
    """En-tete Content-Disposition qui force le telechargement sous `filename`,
    y compris pour un nom non-ASCII (accents, espaces...) : forme ASCII de
    repli + forme RFC 5987 (filename*=UTF-8''...) comprise par les navigateurs."""
    ascii_fallback = filename.encode("ascii", "ignore").decode("ascii").replace('"', "") or "photo.jpg"
    return f"attachment; filename=\"{ascii_fallback}\"; filename*=UTF-8''{quote(filename)}"


class StorageService(ABC):
    @abstractmethod
    async def upload(self, key: str, data: bytes, content_type: str) -> None:
        """Upload les bytes sous `key` (bucket prive)."""

    @abstractmethod
    async def delete(self, key: str) -> None:
        ...

    @abstractmethod
    async def delete_prefix(self, prefix: str) -> int:
        """Supprime tous les objets dont la cle commence par `prefix` (ex:
        tous les fichiers d'un evenement supprime). Renvoie le nombre
        d'objets supprimes."""

    @abstractmethod
    async def download(self, key: str) -> bytes:
        """Recupere les bytes stockes sous `key`."""

    @abstractmethod
    async def get_presigned_url(
        self, key: str, expires_in: int = 3600, download_filename: str | None = None
    ) -> str:
        """URL signee temporaire pour lire `key` (bucket prive). Avec
        `download_filename`, le navigateur telecharge le fichier sous ce nom
        au lieu de l'afficher (lien "Telecharger" d'une photo achetee)."""

    async def get_cacheable_url(self, key: str) -> str:
        """URL signee STABLE pendant une periode (voir LocalS3StorageService) :
        le telephone garde l'image en cache au lieu de la retelecharger a
        chaque visite. Par defaut : URL signee ordinaire."""
        return await self.get_presigned_url(key, expires_in=CACHE_WINDOW_SECONDS * 2)

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """True si `key` existe deja (evite de regenerer un fichier derive,
        ex: crop de visage, deja calcule lors d'un appel precedent)."""


# Apercus, miniatures et vignettes de visages : leur URL signee ne change que
# toutes les 12 h (signature datee du debut de la periode), au lieu de changer
# a chaque requete. Avant (mesure du 04/11), chaque visite retelechargeait
# toutes les images : l'URL etait nouvelle, le cache du navigateur inutile.
CACHE_WINDOW_SECONDS = 12 * 3600


class _FixedTimeQueryAuth(S3SigV4QueryAuth):
    """Signature SigV4 en parametres d'URL, datee d'un instant fixe."""

    def __init__(self, credentials, region: str, expires: int, timestamp: str) -> None:
        super().__init__(credentials, "s3", region, expires=expires)
        self._fixed_timestamp = timestamp

    def add_auth(self, request) -> None:
        request.context["timestamp"] = self._fixed_timestamp
        self._modify_request_before_signing(request)
        canonical_request = self.canonical_request(request)
        string_to_sign = self.string_to_sign(request, canonical_request)
        self._inject_signature_to_request(request, self.signature(string_to_sign, request))


class LocalS3StorageService(StorageService):
    """Stockage S3-compatible (MinIO en local, Cloudflare R2 en ligne).

    boto3 est un client SYNCHRONE : chaque appel reseau (upload, download,
    head, delete) est execute dans un thread via asyncio.to_thread. Appele
    directement depuis une fonction `async`, il bloquait toute la boucle
    d'evenements le temps de l'aller-retour R2 (mesure : /health passait de
    9 ms a 8,8 s pendant un calcul de groupes de visages), plus aucune
    requete n'etait servie pendant ce temps, pour aucun utilisateur. Les
    clients boto3 sont thread-safe ; seule la signature d'URL (calcul local,
    sans reseau) reste executee directement."""

    def __init__(self) -> None:
        boto_config = BotoConfig(
            signature_version="s3v4",
            # Plusieurs threads partagent le meme client (indexation en
            # parallele, telechargements concurrents) : le pool par defaut (10)
            # provoquait des attentes de connexion inutiles.
            max_pool_connections=32,
        )
        self._client = boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint_url,
            aws_access_key_id=settings.s3_access_key,
            aws_secret_access_key=settings.s3_secret_key,
            region_name=settings.s3_region,
            config=boto_config,
        )
        # Client dedie a la signature d'URL, avec l'endpoint PUBLIC : la
        # signature SigV4 couvre l'en-tete Host, donc on ne peut pas signer
        # avec l'hote interne au reseau Docker ("minio") puis reecrire
        # l'origine ensuite (ca invalide la signature -> SignatureDoesNotMatch).
        self._presign_client = boto3.client(
            "s3",
            endpoint_url=settings.s3_public_url,
            aws_access_key_id=settings.s3_access_key,
            aws_secret_access_key=settings.s3_secret_key,
            region_name=settings.s3_region,
            config=boto_config,
        )
        self._bucket = settings.s3_bucket
        self._credentials = Credentials(settings.s3_access_key, settings.s3_secret_key)
        self._ensure_bucket()

    def _ensure_bucket(self) -> None:
        try:
            self._client.head_bucket(Bucket=self._bucket)
        except ClientError:
            self._client.create_bucket(Bucket=self._bucket)
        # Pas de bucket policy publique : le bucket reste prive par defaut.

    async def upload(self, key: str, data: bytes, content_type: str) -> None:
        await asyncio.to_thread(
            self._client.put_object, Bucket=self._bucket, Key=key, Body=data, ContentType=content_type
        )

    async def delete(self, key: str) -> None:
        await asyncio.to_thread(self._client.delete_object, Bucket=self._bucket, Key=key)

    def _delete_prefix_sync(self, prefix: str) -> int:
        deleted = 0
        paginator = self._client.get_paginator("list_objects_v2")
        batch: list[dict] = []
        for page in paginator.paginate(Bucket=self._bucket, Prefix=prefix):
            for obj in page.get("Contents", []):
                batch.append({"Key": obj["Key"]})
                if len(batch) == _S3_DELETE_BATCH:
                    self._client.delete_objects(Bucket=self._bucket, Delete={"Objects": batch, "Quiet": True})
                    deleted += len(batch)
                    batch = []
        if batch:
            self._client.delete_objects(Bucket=self._bucket, Delete={"Objects": batch, "Quiet": True})
            deleted += len(batch)
        return deleted

    async def delete_prefix(self, prefix: str) -> int:
        return await asyncio.to_thread(self._delete_prefix_sync, prefix)

    def _download_sync(self, key: str) -> bytes:
        response = self._client.get_object(Bucket=self._bucket, Key=key)
        return response["Body"].read()

    async def download(self, key: str) -> bytes:
        return await asyncio.to_thread(self._download_sync, key)

    async def get_presigned_url(
        self, key: str, expires_in: int = 3600, download_filename: str | None = None
    ) -> str:
        params = {"Bucket": self._bucket, "Key": key}
        if download_filename:
            params["ResponseContentDisposition"] = content_disposition_attachment(download_filename)
        return self._presign_client.generate_presigned_url("get_object", Params=params, ExpiresIn=expires_in)

    async def get_cacheable_url(self, key: str) -> str:
        now = int(time.time())
        start = now - now % CACHE_WINDOW_SECONDS
        timestamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime(start))
        # Lien valable 2 periodes ; le navigateur garde l'image au plus une
        # periode : elle n'est jamais gardee au-dela de la validite du lien.
        # La duree est fixe, sinon l'URL changerait a chaque requete.
        query = urlencode({"response-cache-control": f"private, max-age={CACHE_WINDOW_SECONDS}"}, quote_via=quote)
        url = f"{settings.s3_public_url.rstrip('/')}/{self._bucket}/{quote(key, safe='/~')}?{query}"
        request = AWSRequest(method="GET", url=url)
        _FixedTimeQueryAuth(self._credentials, settings.s3_region, 2 * CACHE_WINDOW_SECONDS, timestamp).add_auth(request)
        return request.url

    def _exists_sync(self, key: str) -> bool:
        try:
            self._client.head_object(Bucket=self._bucket, Key=key)
            return True
        except ClientError:
            return False

    async def exists(self, key: str) -> bool:
        return await asyncio.to_thread(self._exists_sync, key)


class SupabaseStorageService(StorageService):
    """Stockage Supabase Storage. Necessite SUPABASE_URL et SUPABASE_SERVICE_ROLE_KEY."""

    def __init__(self) -> None:
        if not settings.supabase_url or not settings.supabase_service_role_key:
            raise NotImplementedError(
                "STORAGE_BACKEND=supabase mais SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY "
                "ne sont pas configures. Fournissez ces credentials dans .env, ou utilisez "
                "STORAGE_BACKEND=local (MinIO) en attendant."
            )
        import httpx

        self._bucket = settings.supabase_storage_bucket
        self._base_url = settings.supabase_url.rstrip("/")
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            headers={
                "Authorization": f"Bearer {settings.supabase_service_role_key}",
                "apikey": settings.supabase_service_role_key,
            },
            timeout=30.0,
        )

    async def upload(self, key: str, data: bytes, content_type: str) -> None:
        resp = await self._client.post(
            f"/storage/v1/object/{self._bucket}/{key}",
            content=data,
            headers={"Content-Type": content_type},
        )
        resp.raise_for_status()

    async def delete(self, key: str) -> None:
        resp = await self._client.delete(f"/storage/v1/object/{self._bucket}/{key}")
        resp.raise_for_status()

    async def delete_prefix(self, prefix: str) -> int:
        # L'API Supabase liste un "dossier" a la fois (pas de listing
        # recursif) : on descend dans les sous-dossiers (entrees sans id).
        keys: list[str] = []
        pending = [prefix.rstrip("/")]
        while pending:
            folder = pending.pop()
            offset = 0
            while True:
                resp = await self._client.post(
                    f"/storage/v1/object/list/{self._bucket}",
                    json={"prefix": folder, "limit": 1000, "offset": offset},
                )
                resp.raise_for_status()
                entries = resp.json()
                for entry in entries:
                    path = f"{folder}/{entry['name']}"
                    if entry.get("id") is None:
                        pending.append(path)
                    else:
                        keys.append(path)
                if len(entries) < 1000:
                    break
                offset += 1000
        for i in range(0, len(keys), _S3_DELETE_BATCH):
            resp = await self._client.request(
                "DELETE", f"/storage/v1/object/{self._bucket}", json={"prefixes": keys[i : i + _S3_DELETE_BATCH]}
            )
            resp.raise_for_status()
        return len(keys)

    async def download(self, key: str) -> bytes:
        resp = await self._client.get(f"/storage/v1/object/{self._bucket}/{key}")
        resp.raise_for_status()
        return resp.content

    async def get_presigned_url(
        self, key: str, expires_in: int = 3600, download_filename: str | None = None
    ) -> str:
        resp = await self._client.post(
            f"/storage/v1/object/sign/{self._bucket}/{key}",
            json={"expiresIn": expires_in},
        )
        resp.raise_for_status()
        signed_path = resp.json()["signedURL"]
        url = f"{self._base_url}/storage/v1{signed_path}"
        if download_filename:
            url += f"&download={quote(download_filename)}"
        return url

    async def exists(self, key: str) -> bool:
        resp = await self._client.head(f"/storage/v1/object/{self._bucket}/{key}")
        return resp.status_code == 200


@lru_cache
def get_storage_service() -> StorageService:
    if settings.storage_backend == "supabase":
        return SupabaseStorageService()
    return LocalS3StorageService()
