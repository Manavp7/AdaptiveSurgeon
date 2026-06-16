"""Synthetic demo dataset generator.

Creates users (RBAC), patients, procedures, synthetic surgical videos, and
outcomes, then runs the full analysis pipeline on each so the dashboard is
populated end-to-end out of the box. Fully deterministic and offline.

Ingestion goes through the same storage + model interfaces real de-identified
hospital data would use, so swapping in real cases needs no schema changes.
"""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path

from sqlalchemy.orm import Session

from .. import models
from ..db import SessionLocal, init_db
from ..security import hash_password
from ..services import pipeline
from ..storage import get_store
from .sample_video import render_surgical_video

log = logging.getLogger("adaptivesurgeon.seed")

# (username, password, role, full_name)
_USERS = [
    ("admin", "admin123", "admin", "System Administrator"),
    ("surgeon", "surgeon123", "surgeon", "Dr. A. Surgeon"),
    ("viewer", "viewer123", "viewer", "Read-Only Observer"),
]

# Procedure specs: deterministic seed + surgeon skill drive the synthetic video.
_CASES = [
    {
        "mrn": "MRN-1001", "name": "Patient Alpha", "age": 54, "sex": "F", "bmi": 28.4,
        "history": {"diabetes": "type2", "prior_surgery": "none"},
        "surgeon_id": "S-01", "surgeon": "Dr. Mehta", "skill": 0.92, "seed": 11,
        "duration": 22, "complications": [], "los": 1.5,
        "discharge": "Uncomplicated laparoscopic cholecystectomy. Discharged POD1.",
    },
    {
        "mrn": "MRN-1002", "name": "Patient Bravo", "age": 41, "sex": "M", "bmi": 31.2,
        "history": {"hypertension": "yes", "smoker": "yes"},
        "surgeon_id": "S-02", "surgeon": "Dr. Rao", "skill": 0.55, "seed": 22,
        "duration": 26, "complications": ["minor bleeding"], "los": 2.0,
        "discharge": "Intra-op minor bleeding controlled. Recovered well, discharged POD2.",
    },
    {
        "mrn": "MRN-1003", "name": "Patient Charlie", "age": 63, "sex": "F", "bmi": 26.0,
        "history": {"gallstones": "chronic", "cholecystitis": "acute"},
        "surgeon_id": "S-03", "surgeon": "Dr. Iyer", "skill": 0.30, "seed": 33,
        "duration": 30, "complications": ["bile duct injury", "conversion to open"],
        "los": 5.0, "discharge": "Bile duct injury identified, repaired. Prolonged stay.",
    },
    {
        "mrn": "MRN-1004", "name": "Patient Delta", "age": 48, "sex": "M", "bmi": 24.8,
        "history": {"prior_surgery": "appendectomy"},
        "surgeon_id": "S-01", "surgeon": "Dr. Mehta", "skill": 0.84, "seed": 44,
        "duration": 20, "complications": [], "los": 1.0,
        "discharge": "Routine cholecystectomy, no complications. Day-case discharge.",
    },
    {
        "mrn": "MRN-1005", "name": "Patient Echo", "age": 57, "sex": "F", "bmi": 33.7,
        "history": {"diabetes": "type2", "obesity": "yes"},
        "surgeon_id": "S-02", "surgeon": "Dr. Rao", "skill": 0.68, "seed": 55,
        "duration": 24, "complications": ["wound infection"], "los": 3.0,
        "discharge": "Post-op superficial wound infection, treated with antibiotics.",
    },
]


def _attach_dicom_studies(db: Session, store, procedure_id: str) -> None:
    """Attach real bundled DICOM studies (CT slice + MR volume) to a procedure."""
    try:
        from pydicom.data import get_testdata_file

        from ..services import dicom
    except Exception:  # noqa: BLE001 - pydicom optional
        return

    studies = [("ct", "CT_small.dcm"), ("mr", "emri_small.dcm")]
    for kind, fname in studies:
        try:
            src = get_testdata_file(fname)
            if not src:
                continue
            uri = store.save_file(f"procedures/{procedure_id}/{kind}.dcm", src)
            meta = dicom.read_metadata(src)
            db.add(models.Media(
                procedure_id=procedure_id, kind=kind, uri=uri, filename=fname,
                content_type="application/dicom",
                width=meta.get("cols"), height=meta.get("rows"),
                meta={**meta, "synthetic": False, "source": "pydicom-testdata"},
            ))
        except Exception:  # noqa: BLE001
            continue


def seed_users(db: Session) -> None:
    for username, password, role, full_name in _USERS:
        if db.query(models.User).filter_by(username=username).first():
            continue
        db.add(models.User(
            username=username, role=role, full_name=full_name,
            password_hash=hash_password(password),
        ))
    db.commit()


def seed_cases(db: Session, run_analysis: bool = True) -> list[str]:
    store = get_store()
    proc_ids: list[str] = []
    for spec in _CASES:
        if db.query(models.Patient).filter_by(external_mrn=spec["mrn"]).first():
            log.info("Case %s already seeded; skipping.", spec["mrn"])
            continue

        from ..security_deid import pseudonymize

        patient = models.Patient(
            external_mrn=spec["mrn"], mrn_hash=pseudonymize(spec["mrn"]),
            display_name=spec["name"], age=spec["age"],
            sex=spec["sex"], bmi=spec["bmi"], history=spec["history"],
            consent_obtained=True, consent_reference=f"CONSENT-{spec['mrn']}",
        )
        db.add(patient)
        db.flush()

        proc = models.Procedure(
            patient_id=patient.id, procedure_type="laparoscopic_cholecystectomy",
            surgeon_id=spec["surgeon_id"], surgeon_name=spec["surgeon"],
            status="registered",
            notes=f"Synthetic demo case (technique seed {spec['seed']}).",
        )
        db.add(proc)
        db.flush()

        # Generate + ingest the synthetic video through the object store.
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp) / "surgery.mp4"
            info = render_surgical_video(
                tmp_path, seed=spec["seed"], skill=spec["skill"],
                duration_s=spec["duration"], fps=12,
            )
            uri = store.save_file(f"procedures/{proc.id}/video.mp4", tmp_path)

        media = models.Media(
            procedure_id=proc.id, kind="video", uri=uri, filename="video.mp4",
            content_type="video/mp4", duration_s=info["duration_s"], fps=info["fps"],
            width=info["width"], height=info["height"],
            meta={"synthetic": True, "codec": info["codec"], "skill_seed": spec["skill"]},
        )
        db.add(media)

        # Attach REAL DICOM imaging studies (bundled with pydicom, offline).
        _attach_dicom_studies(db, store, proc.id)

        db.add(models.Outcome(
            procedure_id=proc.id, discharge_summary=spec["discharge"],
            complications=spec["complications"], length_of_stay_days=spec["los"],
            readmission_30d=bool(spec["complications"]) and spec["los"] > 4,
            mortality=False,
        ))
        db.commit()
        proc_ids.append(proc.id)
        log.info("Seeded case %s (procedure %s).", spec["mrn"], proc.id)

        if run_analysis:
            result = pipeline.run_analysis(db, proc.id)
            log.info("Analyzed %s: %s", proc.id, result)

    return proc_ids


def seed_all(run_analysis: bool = True) -> dict:
    init_db()
    db = SessionLocal()
    try:
        seed_users(db)
        proc_ids = seed_cases(db, run_analysis=run_analysis)
        return {
            "users": len(_USERS),
            "procedures_seeded": len(proc_ids),
            "procedure_ids": proc_ids,
            "analyzed": run_analysis,
        }
    finally:
        db.close()


if __name__ == "__main__":  # pragma: no cover
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    print(seed_all())
