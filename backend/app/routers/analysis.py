"""Analysis orchestration + the unified per-procedure analysis payload.

``POST /procedures/{id}/analyze`` runs the full connected pipeline; ``GET
/procedures/{id}/analysis`` returns one payload stitching every subsystem's
output together for the dashboard.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..config import get_settings
from ..db import get_db
from ..models import (
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
    DetectionOut,
    PhaseSegmentOut,
    RiskAssessmentOut,
    SkillReportOut,
    TrackOut,
    UnifiedAnalysis,
)
from ..security import require_role
from ..services import pipeline

router = APIRouter(prefix="/procedures", tags=["analysis"])
settings = get_settings()

_MAX_DETECTIONS = 5000


@router.post("/{procedure_id}/analyze")
def analyze(
    procedure_id: str,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_role("surgeon"))],
) -> dict:
    try:
        return pipeline.run_analysis(db, procedure_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


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
