"""Analysis orchestration + the unified per-procedure analysis payload.

``POST /procedures/{id}/analyze`` runs the full connected pipeline; ``GET
/procedures/{id}/analysis`` returns one payload stitching every subsystem's
output together for the dashboard.
"""

from __future__ import annotations

from typing import Annotated

import csv
import io

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session

from ..config import get_settings
from ..db import get_db
from ..models import (
    AnatomyMask,
    Detection,
    Event,
    Media,
    PhaseSegment,
    Procedure,
    RiskAssessment,
    SkillReport,
    Track,
    User,
)
from ..schemas.analysis import (
    AdvisoryOut,
    AnalysisStatus,
    AnatomyMaskOut,
    DetectionOut,
    PhaseSegmentOut,
    RiskAssessmentOut,
    SkillReportOut,
    TrackOut,
    UnifiedAnalysis,
)
from ..security import require_role
from ..services import pipeline
from ..services.jobs import registry
from ..db import SessionLocal

router = APIRouter(prefix="/procedures", tags=["analysis"])
settings = get_settings()

_MAX_DETECTIONS = 5000


def _run_analysis_job(job_id: str, procedure_id: str) -> None:
    """Background worker: own DB session, reports progress to the registry."""
    registry.update(job_id, status="running", message="Starting")
    db = SessionLocal()
    try:
        result = pipeline.run_analysis(
            db, procedure_id,
            progress_cb=lambda p, m: registry.update(job_id, progress=p, message=m),
        )
        registry.update(job_id, status="done", progress=1.0, result=result, message="Complete")
    except Exception as exc:  # noqa: BLE001
        registry.update(job_id, status="error", error=str(exc), message="Failed")
    finally:
        db.close()


@router.post("/{procedure_id}/analyze")
def analyze(
    procedure_id: str,
    background: BackgroundTasks,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_role("surgeon"))],
    wait: bool = False,
) -> dict:
    proc = db.get(Procedure, procedure_id)
    if not proc:
        raise HTTPException(status_code=404, detail="Procedure not found")
    if wait:
        # Synchronous path (used by tests / smoke / simple clients).
        try:
            return pipeline.run_analysis(db, procedure_id)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    job = registry.create(kind="analysis", target_id=procedure_id)
    background.add_task(_run_analysis_job, job.id, procedure_id)
    return {"job_id": job.id, "status": job.status, "procedure_id": procedure_id}


def _build_report(db: Session, procedure_id: str) -> dict:
    proc = db.get(Procedure, procedure_id)
    if not proc:
        raise HTTPException(status_code=404, detail="Procedure not found")
    skill = db.query(SkillReport).filter_by(procedure_id=procedure_id).first()
    phases = db.query(PhaseSegment).filter_by(procedure_id=procedure_id).order_by(PhaseSegment.order_idx).all()
    risks = db.query(RiskAssessment).filter_by(procedure_id=procedure_id).order_by(RiskAssessment.t_s).all()
    advisories = db.query(Event).filter_by(procedure_id=procedure_id, kind="advisory").count()
    patient = proc.patient
    return {
        "procedure_id": proc.id,
        "procedure_type": proc.procedure_type,
        "surgeon": proc.surgeon_name or proc.surgeon_id,
        "status": proc.status,
        "patient": {
            # de-identified reference only
            "mrn_hash": getattr(patient, "mrn_hash", "") if patient else "",
            "age": patient.age if patient else None,
            "sex": patient.sex if patient else None,
            "consent_obtained": getattr(patient, "consent_obtained", False) if patient else False,
        },
        "skill_score": skill.score if skill else None,
        "skill_subscores": skill.subscores if skill else {},
        "phases": [{"phase": p.phase, "t_start_s": p.t_start_s, "t_end_s": p.t_end_s, "confidence": p.confidence} for p in phases],
        "top_risks": [{"event_type": r.event_type, "probability": r.probability, "t_s": r.t_s, "severity": r.severity} for r in sorted(risks, key=lambda r: -r.probability)[:5]],
        "advisory_count": advisories,
        "outcome": {
            "discharge_summary": proc.outcome.discharge_summary if proc.outcome else "",
            "complications": proc.outcome.complications if proc.outcome else [],
            "length_of_stay_days": proc.outcome.length_of_stay_days if proc.outcome else None,
        } if proc.outcome else None,
        "disclaimer": "ADVISORY ONLY — research prototype, not a medical device. Synthetic data.",
    }


@router.get("/{procedure_id}/report")
def report_json(procedure_id: str, db: Annotated[Session, Depends(get_db)]) -> dict:
    return _build_report(db, procedure_id)


@router.get("/{procedure_id}/report.csv")
def report_csv(procedure_id: str, db: Annotated[Session, Depends(get_db)]):
    rep = _build_report(db, procedure_id)
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["field", "value"])
    w.writerow(["procedure_id", rep["procedure_id"]])
    w.writerow(["procedure_type", rep["procedure_type"]])
    w.writerow(["surgeon", rep["surgeon"]])
    w.writerow(["status", rep["status"]])
    w.writerow(["patient_age", rep["patient"]["age"]])
    w.writerow(["patient_sex", rep["patient"]["sex"]])
    w.writerow(["skill_score", rep["skill_score"]])
    for k, v in (rep["skill_subscores"] or {}).items():
        w.writerow([f"skill_{k}", v])
    for ph in rep["phases"]:
        w.writerow([f"phase_{ph['phase']}", f"{ph['t_start_s']}-{ph['t_end_s']}s (conf {ph['confidence']})"])
    for r in rep["top_risks"]:
        w.writerow([f"risk_{r['event_type']}", f"{int(r['probability']*100)}% @ {r['t_s']}s"])
    w.writerow(["advisory_count", rep["advisory_count"]])
    if rep["outcome"]:
        w.writerow(["complications", "; ".join(str(c) for c in rep["outcome"]["complications"])])
        w.writerow(["length_of_stay_days", rep["outcome"]["length_of_stay_days"]])
    return Response(
        content=buf.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="report_{procedure_id[:8]}.csv"'},
    )


@router.get("/{procedure_id}/analysis/status", response_model=AnalysisStatus)
def analysis_status(procedure_id: str, db: Annotated[Session, Depends(get_db)]) -> AnalysisStatus:
    proc = db.get(Procedure, procedure_id)
    if not proc:
        raise HTTPException(status_code=404, detail="Procedure not found")
    has = db.query(PhaseSegment).filter_by(procedure_id=procedure_id).first() is not None
    return AnalysisStatus(procedure_id=procedure_id, status=proc.status, has_analysis=has)


@router.get("/{procedure_id}/analysis", response_model=UnifiedAnalysis)
def unified_analysis(procedure_id: str, db: Annotated[Session, Depends(get_db)]) -> UnifiedAnalysis:
    proc = db.get(Procedure, procedure_id)
    if not proc:
        raise HTTPException(status_code=404, detail="Procedure not found")

    video = next((m for m in proc.media if m.kind == "video"), None)
    video_uri = (
        f"{settings.api_prefix}/media/{video.id}/content" if video else None
    )

    phases = (
        db.query(PhaseSegment)
        .filter_by(procedure_id=procedure_id)
        .order_by(PhaseSegment.order_idx)
        .all()
    )
    tracks = []
    detections = []
    detection_count = 0
    if video:
        tracks = db.query(Track).filter_by(media_id=video.id).all()
        detection_count = db.query(Detection).filter_by(media_id=video.id).count()
        detections = (
            db.query(Detection)
            .filter_by(media_id=video.id)
            .order_by(Detection.t_s)
            .limit(_MAX_DETECTIONS)
            .all()
        )

    anatomy = db.query(AnatomyMask).filter_by(procedure_id=procedure_id).all()
    skill = db.query(SkillReport).filter_by(procedure_id=procedure_id).first()
    risks = (
        db.query(RiskAssessment)
        .filter_by(procedure_id=procedure_id)
        .order_by(RiskAssessment.t_s)
        .all()
    )
    advisories = (
        db.query(Event)
        .filter_by(procedure_id=procedure_id, kind="advisory")
        .order_by(Event.t_start_s)
        .all()
    )

    return UnifiedAnalysis(
        procedure_id=procedure_id,
        status=proc.status,
        video_uri=video_uri,
        video_duration_s=video.duration_s if video else None,
        fps=video.fps if video else None,
        width=video.width if video else None,
        height=video.height if video else None,
        phases=[PhaseSegmentOut.model_validate(p) for p in phases],
        anatomy=[AnatomyMaskOut.model_validate(a) for a in anatomy],
        tracks=[TrackOut.model_validate(t) for t in tracks],
        detection_count=detection_count,
        detections_sample=[DetectionOut.model_validate(d) for d in detections],
        skill=SkillReportOut.model_validate(skill) if skill else None,
        risks=[RiskAssessmentOut.model_validate(r) for r in risks],
        advisories=[
            AdvisoryOut(
                t_start_s=a.t_start_s, t_end_s=a.t_end_s, label=a.label,
                severity=a.severity, payload=a.payload,
            )
            for a in advisories
        ],
    )
