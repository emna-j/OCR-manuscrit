"""Stockage des fichiers (cahier des charges §16).

Les binaires (documents originaux et prétraités) sont stockés hors base,
derrière une interface commune :
- `LocalStorage`  : système de fichiers local (défaut en développement) ;
- `MinioStorage`  : serveur MinIO / S3 (utilisé en environnement dockerisé).

Le backend est choisi via `STORAGE_BACKEND=local|minio`.
"""
from abc import ABC, abstractmethod
from io import BytesIO
from pathlib import Path

from app.core.config import settings


class StorageBackend(ABC):
    @abstractmethod
    def save(self, key: str, data: bytes, content_type: str) -> str:
        """Persiste un fichier et retourne sa clé."""

    @abstractmethod
    def load(self, key: str) -> bytes:
        """Lit un fichier depuis sa clé."""

    @abstractmethod
    def delete(self, key: str) -> None:
        """Supprime un fichier (idempotent)."""

    @abstractmethod
    def exists(self, key: str) -> bool:
        """Indique si un fichier existe."""


class LocalStorage(StorageBackend):
    """Stockage sur le système de fichiers local (dev / tests)."""

    def __init__(self, root: str | Path) -> None:
        self._root = Path(root).resolve()
        self._root.mkdir(parents=True, exist_ok=True)

    def _resolve(self, key: str) -> Path:
        # Anti path-traversal : la clé doit rester sous la racine.
        path = (self._root / key).resolve()
        if not str(path).startswith(str(self._root)):
            raise ValueError("Invalid storage key")
        return path

    def save(self, key: str, data: bytes, content_type: str) -> str:
        path = self._resolve(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return key

    def load(self, key: str) -> bytes:
        return self._resolve(key).read_bytes()

    def delete(self, key: str) -> None:
        path = self._resolve(key)
        if path.exists():
            path.unlink()

    def exists(self, key: str) -> bool:
        return self._resolve(key).exists()


class MinioStorage(StorageBackend):
    """Stockage MinIO (compatible S3)."""

    def __init__(
        self,
        endpoint: str,
        access_key: str,
        secret_key: str,
        bucket: str,
        secure: bool = False,
    ) -> None:
        from minio import Minio

        self._bucket = bucket
        self._client = Minio(endpoint, access_key=access_key, secret_key=secret_key, secure=secure)
        if not self._client.bucket_exists(bucket):
            self._client.make_bucket(bucket)

    def save(self, key: str, data: bytes, content_type: str) -> str:
        self._client.put_object(self._bucket, key, BytesIO(data), length=len(data), content_type=content_type)
        return key

    def load(self, key: str) -> bytes:
        response = self._client.get_object(self._bucket, key)
        try:
            return response.read()
        finally:
            response.close()
            response.release_conn()

    def delete(self, key: str) -> None:
        from minio.error import S3Error

        try:
            self._client.remove_object(self._bucket, key)
        except S3Error:
            pass

    def exists(self, key: str) -> bool:
        from minio.error import S3Error

        try:
            self._client.stat_object(self._bucket, key)
            return True
        except S3Error:
            return False


def get_storage() -> StorageBackend:
    """Instancie le backend de stockage configuré."""
    if settings.storage_backend == "minio":
        return MinioStorage(
            endpoint=settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            bucket=settings.minio_bucket_documents,
            secure=settings.minio_secure,
        )
    return LocalStorage(settings.storage_local_dir)