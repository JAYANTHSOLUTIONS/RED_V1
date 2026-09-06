"""Storage module exposing StorageBackend and factory."""
from typing import Optional

from app.core.config import Settings, get_settings
from app.storage.base import StorageBackend
from app.storage.local import LocalStorageBackend
from app.storage.s3 import S3StorageBackend


def get_storage_backend(settings: Optional[Settings] = None) -> StorageBackend:
    """Factory creating the configured storage backend."""
    cfg = settings or get_settings()
    backend_type = (cfg.STORAGE_BACKEND or "local").lower().strip()

    if backend_type == "s3":
        return S3StorageBackend(cfg)
    return LocalStorageBackend(base_dir=cfg.LOCAL_DOCUMENTS_DIR)


__all__ = [
    "StorageBackend",
    "LocalStorageBackend",
    "S3StorageBackend",
    "get_storage_backend",
]
