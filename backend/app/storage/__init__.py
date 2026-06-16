"""Object-storage abstraction.

A single ``ObjectStore`` interface with a local-filesystem implementation today
and an S3/MinIO-compatible implementation later. Code that stores/loads media
depends only on the interface, so swapping backends needs no architectural change.
"""

from __future__ import annotations

from .base import ObjectStore
from .local import LocalObjectStore
from ..config import get_settings

_store: ObjectStore | None = None


def get_store() -> ObjectStore:
    global _store
    if _store is None:
        settings = get_settings()
        if settings.storage_backend == "s3":
            # Future: from .s3 import S3ObjectStore; _store = S3ObjectStore(...)
            raise NotImplementedError(
                "S3/MinIO backend not enabled in this build; use storage_backend=local"
            )
        _store = LocalObjectStore(settings.storage_dir)
    return _store


__all__ = ["ObjectStore", "LocalObjectStore", "get_store"]
