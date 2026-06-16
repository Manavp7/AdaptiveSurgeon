"""Local filesystem object store.

URIs look like ``local://<relative/key>``. The relative key maps directly to a
path under the configured storage directory.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from .base import ObjectStore

SCHEME = "local://"


class LocalObjectStore(ObjectStore):
    def __init__(self, root: str | Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    # --- helpers ---
    def _key_to_path(self, key: str) -> Path:
        key = key.lstrip("/")
        path = (self.root / key).resolve()
        # Prevent path traversal outside the storage root.
        if not str(path).startswith(str(self.root.resolve())):
            raise ValueError(f"Illegal storage key: {key}")
        return path

    def _uri(self, key: str) -> str:
        return f"{SCHEME}{key.lstrip('/')}"

    def _uri_to_key(self, uri: str) -> str:
        if not uri.startswith(SCHEME):
            raise ValueError(f"Not a local store URI: {uri}")
        return uri[len(SCHEME):]

    # --- interface ---
    def save_bytes(self, key: str, data: bytes) -> str:
        path = self._key_to_path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return self._uri(key)

    def save_file(self, key: str, src_path: str | Path) -> str:
        path = self._key_to_path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src_path, path)
        return self._uri(key)

    def open_path(self, uri: str) -> Path:
        return self._key_to_path(self._uri_to_key(uri))

    def exists(self, uri: str) -> bool:
        try:
            return self.open_path(uri).exists()
        except ValueError:
            return False

    def delete(self, uri: str) -> None:
        path = self.open_path(uri)
        if path.exists():
            path.unlink()
