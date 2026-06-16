"""Storage adapter tests (local round-trip + S3 URI logic without boto3)."""

from __future__ import annotations

import tempfile
from pathlib import Path

from app.storage.local import LocalObjectStore
from app.storage.s3 import S3ObjectStore


def test_local_store_roundtrip():
    with tempfile.TemporaryDirectory() as d:
        store = LocalObjectStore(d)
        uri = store.save_bytes("a/b/c.txt", b"hello")
        assert uri.startswith("local://")
        assert store.exists(uri)
        assert store.open_path(uri).read_bytes() == b"hello"
        store.delete(uri)
        assert not store.exists(uri)


def test_local_store_prevents_traversal():
    with tempfile.TemporaryDirectory() as d:
        store = LocalObjectStore(d)
        try:
            store.save_bytes("../../etc/evil", b"x")
            assert False, "expected traversal to be blocked"
        except ValueError:
            pass


def test_s3_uri_logic_without_boto3():
    # bypass __init__ (which needs boto3) to test pure URI mapping
    store = S3ObjectStore.__new__(S3ObjectStore)
    store.bucket = "adaptivesurgeon"
    assert store._uri("procedures/x/video.mp4") == "s3://adaptivesurgeon/procedures/x/video.mp4"
    assert store._uri_to_key("s3://adaptivesurgeon/procedures/x/video.mp4") == "procedures/x/video.mp4"
