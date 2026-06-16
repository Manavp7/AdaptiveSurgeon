"""Object-store interface."""

from __future__ import annotations

import abc
from pathlib import Path


class ObjectStore(abc.ABC):
    """Stable storage contract. URIs are opaque keys (e.g. ``local://...``)."""

    @abc.abstractmethod
    def save_bytes(self, key: str, data: bytes) -> str:
        """Persist raw bytes under ``key``; return the canonical URI."""

    @abc.abstractmethod
    def save_file(self, key: str, src_path: str | Path) -> str:
        """Persist a file from disk under ``key``; return the canonical URI."""

    @abc.abstractmethod
    def open_path(self, uri: str) -> Path:
        """Return a local filesystem path for ``uri`` (for reading/streaming)."""

    @abc.abstractmethod
    def exists(self, uri: str) -> bool:
        ...

    @abc.abstractmethod
    def delete(self, uri: str) -> None:
        ...
