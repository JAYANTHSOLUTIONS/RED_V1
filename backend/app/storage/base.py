"""Storage backend abstraction.

Separates file storage mechanics from document business logic, allowing seamless
switching between local filesystem storage and S3-compatible object storage.
"""
from abc import ABC, abstractmethod
from typing import AsyncIterator, Optional, Tuple


class StorageBackend(ABC):
    """Abstract interface for storing, retrieving, and managing document binaries."""

    @abstractmethod
    async def store(self, key: str, data: bytes, content_type: str) -> str:
        """Store binary data under the specified key.

        Returns the storage key.
        """
        pass

    @abstractmethod
    async def retrieve(self, key: str) -> bytes:
        """Retrieve binary data stored under the specified key.

        Raises StorageError or NotFoundError if unavailable.
        """
        pass

    @abstractmethod
    async def get_stream(self, key: str) -> Tuple[AsyncIterator[bytes], int, str]:
        """Return an async chunk generator, file size, and content type for streaming downloads."""
        pass

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Check whether an object exists under the specified key."""
        pass

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Delete an object under the specified key.

        Used for rollback and compensation cleanup when database transactions fail.
        """
        pass

    @abstractmethod
    async def generate_presigned_url(self, key: str, expires_in: int = 900) -> Optional[str]:
        """Generate a short-lived presigned URL if supported by backend (None for local)."""
        pass
