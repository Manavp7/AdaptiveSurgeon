"""Schemas for AI analysis outputs (Subsystems 2,4,5,7) and the unified payload."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class DetectionOut(ORMModel):
    frame_idx: int
    t_s: float
    class_name: str
    confidence: float
    x: float
    y: float
    w: float
    h: float


class TrackOut(ORMModel):
    track_id: int
    class_name: str
    path_length_m: float
    mean_speed_cm_s: float
    max_speed_cm_s: float
    idle_time_s: float
    active_time_s: float
    jerk: float
    points: list


class PhaseSegmentOut(ORMModel):
    phase: str
    order_idx: int
    t_start_s: float
    t_end_s: float
    confidence: float


class SkillReportOut(ORMModel):
    score: float
    surgeon_id: str
    subscores: dict
    findings: list


class RiskAssessmentOut(ORMModel):
    t_s: float
    event_type: str
    probability: float
    severity: str
    drivers: list


class AdvisoryOut(BaseModel):
    t_start_s: float
    t_end_s: float | None = None
    label: str
    severity: str
    payload: dict = {}


class AnalysisStatus(BaseModel):
    procedure_id: str
    status: str
    has_analysis: bool


class UnifiedAnalysis(BaseModel):
    """The single connected payload the dashboard renders per procedure."""

    procedure_id: str
    status: str
    video_uri: str | None = None
    video_duration_s: float | None = None
    fps: float | None = None
    width: int | None = None
    height: int | None = None
    phases: list[PhaseSegmentOut] = []
    tracks: list[TrackOut] = []
    detection_count: int = 0
    detections_sample: list[DetectionOut] = []
    skill: SkillReportOut | None = None
    risks: list[RiskAssessmentOut] = []
    advisories: list[AdvisoryOut] = []
