"""End-to-end analysis pipeline — the single connected workflow.

For a procedure with an uploaded video this runs, in order:

    detect instruments -> track + analytics -> phase timeline -> skill ->
    risk -> copilot advisories -> digital twin -> case embedding

and persists every result so the dashboard renders one connected story. This is
the spine of the Surgical Intelligence OS: each subsystem consumes the previous
subsystem's output rather than living as an isolated demo.
"""

from __future__ import annotations

import logging
from collections.abc import Callable

from sqlalchemy import delete
from sqlalchemy.orm import Session

from .. import models
from ..config import get_settings
import numpy as np

from ..providers import (
    get_anatomy_provider,
    get_copilot_provider,
    get_instrument_provider,
    get_phase_provider,
    get_risk_provider,
)
from ..storage import get_store
from . import foundation, twin, video_intel
from .skill import compute_skill
from .tracking import CentroidTracker

log = logging.getLogger("adaptivesurgeon.pipeline")
settings = get_settings()


def _clear_prior_analysis(db: Session, proc: models.Procedure, media_ids: list[str]) -> None:
    if media_ids:
        db.execute(delete(models.Detection).where(models.Detection.media_id.in_(media_ids)))
        db.execute(delete(models.Track).where(models.Track.media_id.in_(media_ids)))
    db.execute(delete(models.PhaseSegment).where(models.PhaseSegment.procedure_id == proc.id))
    db.execute(delete(models.AnatomyMask).where(models.AnatomyMask.procedure_id == proc.id))
    db.execute(delete(models.RiskAssessment).where(models.RiskAssessment.procedure_id == proc.id))
    db.execute(delete(models.SkillReport).where(models.SkillReport.procedure_id == proc.id))
    db.execute(delete(models.DigitalTwin).where(models.DigitalTwin.procedure_id == proc.id))
    # Remove derived events (keep manual annotations + complications).
    db.execute(
        delete(models.Event).where(
            models.Event.procedure_id == proc.id,
            models.Event.kind.in_(["phase", "advisory", "risk"]),
        )
    )
    db.flush()


def run_analysis(
    db: Session,
    procedure_id: str,
    progress_cb: Callable[[float, str], None] | None = None,
) -> dict:
    def progress(p: float, msg: str) -> None:
        if progress_cb:
            progress_cb(p, msg)

    proc = db.get(models.Procedure, procedure_id)
    if proc is None:
        raise ValueError(f"Procedure not found: {procedure_id}")

    video = next((m for m in proc.media if m.kind == "video"), None)
    if video is None:
        raise ValueError("Procedure has no video media to analyze.")

    proc.status = "processing"
    db.flush()
    progress(0.1, "Reading video")

    store = get_store()
    video_path = store.open_path(video.uri)

    detector = get_instrument_provider()
    va = video_intel.analyze_video(video_path, detector, settings.analysis_sample_fps)
    progress(0.5, "Instruments detected")

    media_ids = [m.id for m in proc.media]
    _clear_prior_analysis(db, proc, media_ids)

    # --- persist detections + build timeline ---
    detection_timeline: list[dict] = []
    n_detections = 0
    frame_diag = (va.width**2 + va.height**2) ** 0.5 or 1.0
    tracker = CentroidTracker(settings.pixels_per_meter, frame_diag)

    for fd in va.frames:
        classes = []
        for d in fd.detections:
            db.add(models.Detection(
                media_id=video.id, frame_idx=fd.frame_idx, t_s=fd.t_s,
                class_name=d.class_name, confidence=d.confidence,
                x=d.x, y=d.y, w=d.w, h=d.h,
            ))
            classes.append(d.class_name)
            n_detections += 1
        tracker.update(fd.t_s, fd.detections)
        detection_timeline.append({"t_s": fd.t_s, "classes": classes})

    # --- anatomy segmentation (Subsystem 3) ---
    anatomy_provider = get_anatomy_provider()
    rep_frame = va.representative_frame
    if rep_frame is None:
        rep_frame = np.zeros((max(va.height, 1), max(va.width, 1), 3), dtype=np.uint8)
    rep_t = va.duration_s / 2.0
    for mask in anatomy_provider.segment(rep_frame, rep_t):
        db.add(models.AnatomyMask(
            procedure_id=proc.id, t_s=round(rep_t, 2), class_name=mask.class_name,
            criticality=mask.criticality, confidence=mask.confidence, polygon=mask.polygon,
        ))

    progress(0.6, "Tracking instruments")
    # --- tracks + analytics ---
    track_metrics = tracker.metrics()
    for m in track_metrics:
        db.add(models.Track(
            media_id=video.id, track_id=m.track_id, class_name=m.class_name,
            path_length_m=m.path_length_m, mean_speed_cm_s=m.mean_speed_cm_s,
            max_speed_cm_s=m.max_speed_cm_s, idle_time_s=m.idle_time_s,
            active_time_s=m.active_time_s, jerk=m.jerk, points=m.points,
        ))

    # --- phase timeline ---
    phase_provider = get_phase_provider()
    phase_results = phase_provider.phases(
        proc.procedure_type, va.duration_s,
        [m.__dict__ for m in track_metrics], detection_timeline,
    )
    phases_dicts = []
    for p in phase_results:
        db.add(models.PhaseSegment(
            procedure_id=proc.id, phase=p.phase, order_idx=p.order_idx,
            t_start_s=p.t_start_s, t_end_s=p.t_end_s, confidence=p.confidence,
        ))
        db.add(models.Event(
            procedure_id=proc.id, kind="phase", label=p.phase,
            t_start_s=p.t_start_s, t_end_s=p.t_end_s, severity="info",
            payload={"confidence": p.confidence, "order_idx": p.order_idx},
        ))
        phases_dicts.append({
            "phase": p.phase, "order_idx": p.order_idx,
            "t_start_s": p.t_start_s, "t_end_s": p.t_end_s, "confidence": p.confidence,
        })

    progress(0.75, "Scoring skill & risk")
    # --- skill ---
    skill = compute_skill(track_metrics, phases_dicts, va.duration_s, va.camera_motion)
    db.add(models.SkillReport(
        procedure_id=proc.id, surgeon_id=proc.surgeon_id,
        score=skill.score, subscores=skill.subscores, findings=skill.findings,
    ))

    # --- risk (features assembled from motion analytics) ---
    motion_intensity = _normalize(
        sum(m.mean_speed_cm_s for m in track_metrics) / max(len(track_metrics), 1), 25.0
    )
    tremor = _normalize(
        sum(m.jerk for m in track_metrics) / max(len(track_metrics), 1), 35.0
    )
    risk_provider = get_risk_provider()
    risk_results = risk_provider.assess({
        "phases": phases_dicts,
        "motion_intensity": motion_intensity,
        "tremor": tremor,
    })
    risks_dicts = []
    for r in risk_results:
        db.add(models.RiskAssessment(
            procedure_id=proc.id, t_s=r.t_s, event_type=r.event_type,
            probability=r.probability, severity=r.severity, drivers=r.drivers,
        ))
        db.add(models.Event(
            procedure_id=proc.id, kind="risk", label=r.event_type,
            t_start_s=r.t_s, severity=r.severity,
            payload={"probability": r.probability, "drivers": r.drivers},
        ))
        risks_dicts.append({"t_s": r.t_s, "event_type": r.event_type, "probability": r.probability})

    # --- copilot advisories ---
    copilot = get_copilot_provider()
    advisories = copilot.advise({"phases": phases_dicts, "risks": risks_dicts,
                                 "procedure_type": proc.procedure_type})
    for a in advisories:
        db.add(models.Event(
            procedure_id=proc.id, kind="advisory", label=a.label,
            t_start_s=a.t_start_s, t_end_s=a.t_end_s, severity=a.severity,
            payload=a.payload,
        ))

    progress(0.9, "Building digital twin")
    # --- digital twin ---
    twin_data = twin.build_twin(proc.id, proc.procedure_type,
                                proc.patient.history if proc.patient else {})
    db.add(models.DigitalTwin(
        procedure_id=proc.id, source_modality=twin_data["source_modality"],
        structures=twin_data["structures"], mesh_uri=twin_data["mesh_uri"],
        expected_vs_actual=twin_data["expected_vs_actual"],
    ))

    # --- update media metadata ---
    video.width = va.width
    video.height = va.height
    video.fps = va.fps
    video.duration_s = va.duration_s

    # --- foundation embedding (attach phase labels for richer summary) ---
    proc.__dict__["_phase_labels"] = [p.phase for p in phase_results]
    foundation.upsert_case_embedding(db, proc)

    proc.status = "analyzed"
    db.commit()
    progress(1.0, "Complete")

    return {
        "procedure_id": proc.id,
        "status": proc.status,
        "detections": n_detections,
        "tracks": len(track_metrics),
        "phases": len(phase_results),
        "skill_score": skill.score,
        "risks": len(risk_results),
        "advisories": len(advisories),
    }


def _normalize(value: float, ref: float) -> float:
    return max(0.0, min(1.0, value / ref)) if ref else 0.0
