"""S3/MinIO-compatible object store (optional).

Implements the same ObjectStore interface as the local backend using boto3. Not
used in the offline default (storage_backend=local); enabled by setting
``ADAPTIVE_STORAGE_BACKEND=s3`` with S3/MinIO credentials. boto3 is imported
lazily so it is not required for the default install.

URIs look like ``s3://<bucket>/<key>``. ``open_path`` downloads to a local temp
file (so existing video-streaming code keeps working unchanged).
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from ..config import get_settings
from .base import ObjectStore

SCHEME = "s3://"


class S3ObjectStore(ObjectStore):
    def __init__(self):
        import boto3  # lazy import; only needed when this backend is enabled

        settings = get_settings()
        self.bucket = settings.s3_bucket
        self._client = boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint_url,
            aws_access_key_id=settings.s3_access_key,
            aws_secret_access_key=settings.s3_secret_key,
        )
        self._tmp = Path(tempfile.gettempdir()) / "adaptivesurgeon_s3cache"
        self._tmp.mkdir(parents=True, exist_ok=True)
        try:
            self._client.head_bucket(Bucket=self.bucket)
        except Exception:
            try:
                self._client.create_bucket(Bucket=self.bucket)
            except Exception:
                pass

    def _uri(self, key: str) -> str:
        return f"{SCHEME}{self.bucket}/{key.lstrip('/')}"

    def _uri_to_key(self, uri: str) -> str:
        if not uri.startswith(SCHEME):
            raise ValueError(f"Not an s3 URI: {uri}")
        _, _, rest = uri[len(SCHEME):].partition("/")
        return rest

    def save_bytes(self, key: str, data: bytes) -> str:
        key = key.lstrip("/")
        self._client.put_object(Bucket=self.bucket, Key=key, Body=data)
        return self._uri(key)

    def save_file(self, key: str, src_path: str | Path) -> str:
        key = key.lstrip("/")
        self._client.upload_file(str(src_path), self.bucket, key)
        return self._uri(key)

    def open_path(self, uri: str) -> Path:
        key = self._uri_to_key(uri)
        local = self._tmp / key.replace("/", "_")
        if not local.exists():
            local.parent.mkdir(parents=True, exist_ok=True)
            self._client.download_file(self.bucket, key, str(local))
        return local

    def exists(self, uri: str) -> bool:
        try:
            self._client.head_object(Bucket=self.bucket, Key=self._uri_to_key(uri))
            return True
        except Exception:
            return False

    def delete(self, uri: str) -> None:
        self._client.delete_object(Bucket=self.bucket, Key=self._uri_to_key(uri))
