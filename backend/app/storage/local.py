"""Local filesystem storage backend.

Stores files under a configurable root directory with strict path traversal defense,
safe streaming, and compensation cleanup.
"""
import mimetypes
import os
from pathlib import Path
from typing import AsyncIterator, Optional, Tuple

from app.core.exceptions import NotFoundError, StorageError
from app.storage.base import StorageBackend


class LocalStorageBackend(StorageBackend):
    """Local filesystem implementation of StorageBackend."""

    def __init__(self, base_dir: str = "storage/documents"):
        self.base_dir = Path(base_dir).resolve()
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _resolve_safe_path(self, key: str) -> Path:
        """Resolve storage key to an absolute Path, preventing path traversal attacks."""
        clean_key = key.lstrip("/\\")
        resolved = (self.base_dir / clean_key).resolve()

        # Guard against directory traversal
        try:
            resolved.relative_to(self.base_dir)
        except ValueError:
            raise StorageError("Invalid storage path: path traversal detected.")

        return resolved

    async def store(self, key: str, data: bytes, content_type: str) -> str:
        """Store binary bytes under the given key."""
        target_path = self._resolve_safe_path(key)
        try:
            target_path.parent.mkdir(parents=True, exist_ok=True)
            with open(target_path, "wb") as f:
                f.write(data)
            return key
        except OSError as exc:
            raise StorageError(f"Failed to write document to local storage: {exc}") from exc

    async def retrieve(self, key: str) -> bytes:
        """Retrieve binary bytes for the given key."""
        target_path = self._resolve_safe_path(key)
        if not target_path.is_file():
            raise NotFoundError("Stored document file was not found on storage backend.")

        try:
            with open(target_path, "rb") as f:
                return f.read()
        except OSError as exc:
            raise StorageError(f"Failed to read document from local storage: {exc}") from exc

    async def get_stream(self, key: str) -> Tuple[AsyncIterator[bytes], int, str]:
        """Return an async chunk generator, file size, and content type."""
        target_path = self._resolve_safe_path(key)
        if not target_path.is_file():
            raise NotFoundError("Stored document file was not found on storage backend.")

        try:
            file_size = target_path.stat().st_size
            guessed_type, _ = mimetypes.guess_type(str(target_path))
            content_type = guessed_type or "application/octet-stream"

            async def file_chunk_generator(chunk_size: int = 64 * 1024) -> AsyncIterator[bytes]:
                with open(target_path, "rb") as f:
                    while True:
                        chunk = f.read(chunk_size)
                        if not chunk:
                            break
                        yield chunk

            return file_chunk_generator(), file_size, content_type
        except OSError as exc:
            raise StorageError(f"Failed to open document stream from local storage: {exc}") from exc

    async def exists(self, key: str) -> bool:
        """Check whether file exists."""
        try:
            target_path = self._resolve_safe_path(key)
            return target_path.is_file()
        except StorageError:
            return False

    async def delete(self, key: str) -> bool:
        """Delete file if it exists. Used for compensation cleanup."""
        try:
            target_path = self._resolve_safe_path(key)
            if target_path.is_file():
                target_path.unlink()
            return True
        except OSError as exc:
            raise StorageError(f"Failed to delete document from local storage: {exc}") from exc

    async def generate_presigned_url(self, key: str, expires_in: int = 900) -> Optional[str]:
        """Local storage does not provide presigned URLs; downloads go through the API."""
        return None
