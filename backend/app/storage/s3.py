"""S3-compatible Object Storage backend readiness.

Provides an object-storage implementation structure for future cloud deployment
(AWS S3, MinIO, Cloudflare R2, DigitalOcean Spaces) without requiring cloud credentials
or cloud SDKs for local development.
"""
from typing import AsyncIterator, Optional, Tuple

from app.core.config import Settings, get_settings
from app.core.exceptions import StorageError
from app.storage.base import StorageBackend


class S3StorageBackend(StorageBackend):
    """S3-compatible object storage provider."""

    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or get_settings()
        self.bucket = self.settings.STORAGE_BUCKET
        self.region = self.settings.STORAGE_REGION
        self.endpoint_url = self.settings.STORAGE_ENDPOINT_URL or None

    def _ensure_client(self):
        try:
            import boto3  # type: ignore
        except ImportError as exc:
            raise StorageError(
                "S3 storage backend requires the 'boto3' package to be installed."
            ) from exc

        if not self.bucket:
            raise StorageError("S3 storage backend requires STORAGE_BUCKET to be configured.")

    async def store(self, key: str, data: bytes, content_type: str) -> str:
        self._ensure_client()
        raise NotImplementedError("S3 cloud storage integration configured for future production phase.")

    async def retrieve(self, key: str) -> bytes:
        self._ensure_client()
        raise NotImplementedError("S3 cloud storage integration configured for future production phase.")

    async def get_stream(self, key: str) -> Tuple[AsyncIterator[bytes], int, str]:
        self._ensure_client()
        raise NotImplementedError("S3 cloud storage integration configured for future production phase.")

    async def exists(self, key: str) -> bool:
        self._ensure_client()
        return False

    async def delete(self, key: str) -> bool:
        self._ensure_client()
        return True

    async def generate_presigned_url(self, key: str, expires_in: int = 900) -> Optional[str]:
        self._ensure_client()
        return None
