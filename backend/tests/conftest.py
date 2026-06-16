"""Pytest fixtures.

Sets an isolated SQLite DB + storage dir via env BEFORE importing the app, so
tests never touch the dev database. Seeds users and one fully-analyzed
procedure (short synthetic video) for fast, deterministic API tests.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest

# --- isolate environment before any app import ---
_TMP = tempfile.mkdtemp(prefix="adaptive_test_")
os.environ["ADAPTIVE_DATABASE_URL"] = f"sqlite:///{_TMP}/test.db"
os.environ["ADAPTIVE_STORAGE_DIR"] = f"{_TMP}/storage"

import warnings  # noqa: E402

warnings.filterwarnings("ignore")

from fastapi.testclient import TestClient  # noqa: E402

from app import models  # noqa: E402
from app.db import SessionLocal, init_db  # noqa: E402
from app.main import app  # noqa: E402
from app.security import hash_password  # noqa: E402
from app.seed.sample_video import render_surgical_video  # noqa: E402
from app.services import pipeline  # noqa: E402
from app.storage import get_store  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _seed():
    init_db()
    db = SessionLocal()
    try:
        for username, role in [("admin", "admin"), ("surgeon", "surgeon"), ("viewer", "viewer")]:
            db.add(models.User(username=username, role=role,
                               password_hash=hash_password(username + "123")))
        db.commit()

        store = get_store()
        for mrn, skill, comps in [("T-1", 0.9, []), ("T-2", 0.3, ["minor bleeding"])]:
            patient = models.Patient(external_mrn=mrn, display_name=f"Test {mrn}", age=50, sex="F")
            db.add(patient)
            db.flush()
            proc = models.Procedure(patient_id=patient.id,
                                    procedure_type="laparoscopic_cholecystectomy",
                                    surgeon_name="Dr. Test")
            db.add(proc)
            db.flush()
            tmp = Path(_TMP) / f"{mrn}.mp4"
            info = render_surgical_video(tmp, seed=int(skill * 100), skill=skill,
                                         duration_s=8, fps=12)
            uri = store.save_file(f"procedures/{proc.id}/video.mp4", tmp)
            db.add(models.Media(procedure_id=proc.id, kind="video", uri=uri,
                                filename="video.mp4", content_type="video/mp4",
                                duration_s=info["duration_s"], fps=info["fps"],
                                width=info["width"], height=info["height"]))
            db.add(models.Outcome(procedure_id=proc.id, discharge_summary="Test case.",
                                  complications=comps))
            from app.seed.demo import _attach_dicom_studies
            _attach_dicom_studies(db, store, proc.id)
            db.commit()
            pipeline.run_analysis(db, proc.id)
    finally:
        db.close()
    yield


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def surgeon_token(client):
    r = client.post("/api/auth/login", data={"username": "surgeon", "password": "surgeon123"})
    return r.json()["access_token"]


@pytest.fixture
def viewer_token(client):
    r = client.post("/api/auth/login", data={"username": "viewer", "password": "viewer123"})
    return r.json()["access_token"]
