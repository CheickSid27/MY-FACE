"""Abstraction de stockage fichiers.

Deux implementations :
- LocalS3StorageService : MinIO (S3-compatible), fonctionnel en dev/self-host.
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

from abc import ABC, abstractmethod
from functools import lru_cache

import boto3
from botocore.client import Config as BotoConfig
from botocore.exceptions import ClientError

from app.core.config import get_settings

settings = get_settings()


class StorageService(ABC):
    @abstractmethod
    async def upload(self, key: str, data: bytes, content_type: str) -> None:
        """Upload les bytes sous `key` (bucket prive)."""

    @abstractmethod
    async def delete(self, key: str) -> None:
        ...

    @abstractmethod
    async def download(self, key: str) -> bytes:
        """Recupere les bytes stockes sous `key`."""

    @abstractmethod
    async def get_presigned_url(self, key: str, expires_in: int = 3600) -> str:
        """URL signee temporaire pour lire `key` (bucket prive)."""


class LocalS3StorageService(StorageService):
    """Stockage S3-compatible local (MinIO), utilise par defaut en dev."""

    def __init__(self) -> None:
        self._client = boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint_url,
            aws_access_key_id=settings.s3_access_key,
            aws_secret_access_key=settings.s3_secret_key,
            region_name=settings.s3_region,
            config=BotoConfig(signature_version="s3v4"),
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
            config=BotoConfig(signature_version="s3v4"),
        )
        self._bucket = settings.s3_bucket
        self._ensure_bucket()

    def _ensure_bucket(self) -> None:
        try:
            self._client.head_bucket(Bucket=self._bucket)
        except ClientError:
            self._client.create_bucket(Bucket=self._bucket)
        # Pas de bucket policy publique : le bucket reste prive par defaut.

    async def upload(self, key: str, data: bytes, content_type: str) -> None:
        self._client.put_object(Bucket=self._bucket, Key=key, Body=data, ContentType=content_type)

    async def delete(self, key: str) -> None:
        self._client.delete_object(Bucket=self._bucket, Key=key)

    async def download(self, key: str) -> bytes:
        response = self._client.get_object(Bucket=self._bucket, Key=key)
        return response["Body"].read()

    async def get_presigned_url(self, key: str, expires_in: int = 3600) -> str:
        return self._presign_client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self._bucket, "Key": key},
            ExpiresIn=expires_in,
        )


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

    async def download(self, key: str) -> bytes:
        resp = await self._client.get(f"/storage/v1/object/{self._bucket}/{key}")
        resp.raise_for_status()
        return resp.content

    async def get_presigned_url(self, key: str, expires_in: int = 3600) -> str:
        resp = await self._client.post(
            f"/storage/v1/object/sign/{self._bucket}/{key}",
            json={"expiresIn": expires_in},
        )
        resp.raise_for_status()
        signed_path = resp.json()["signedURL"]
        return f"{self._base_url}/storage/v1{signed_path}"


@lru_cache
def get_storage_service() -> StorageService:
    if settings.storage_backend == "supabase":
        return SupabaseStorageService()
    return LocalS3StorageService()
