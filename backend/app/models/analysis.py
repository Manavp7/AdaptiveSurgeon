"""AI analysis output models (Subsystems 2-9 persistence).

These tables store the results produced by the pluggable providers so the
dashboard can render a single connected workflow per procedure.
"""

from __future__ import annotations

from sqlalchemy import JSON, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base
from .base import IdMixin, TimestampMixin


class Detection(IdMixin, Base):
    """Per-frame instrument detection (Subsystem 2)."""

    __tablename__ = "detections"

    media_id: Mapped[str] = mapped_column(
        ForeignKey("media.id", ondelete="CASCADE"), index=True
    )
    frame_idx: Mapped[int] = mapped_column(Integer)
    t_s: Mapped[float] = mapped_column(Float)
    class_name: Mapped[str] = mapped_column(String(40), index=True)
    confidence: Mapped[float] = mapped_column(Float, default=1.0)
    # normalized [0,1] bbox
    x: Mapped[float] = mapped_column(Float)
    y: Mapped[float] = mapped_column(Float)
    w: Mapped[float] = mapped_column(Float)
    h: Mapped[float] = mapped_column(Float)


class Track(IdMixin, Base):
    """Per-instrument track + motion analytics (Subsystem 2)."""

    __tablename__ = "tracks"

    media_id: Mapped[str] = mapped_column(
        ForeignKey("media.id", ondelete="CASCADE"), index=True
    )
    track_id: Mapped[int] = mapped_column(Integer)
    class_name: Mapped[str] = mapped_column(String(40), index=True)
    path_length_m: Mapped[float] = mapped_column(Float, default=0.0)
    mean_speed_cm_s: Mapped[float] = mapped_column(Float, default=0.0)
    max_speed_cm_s: Mapped[float] = mapped_column(Float, default=0.0)
    idle_time_s: Mapped[float] = mapped_column(Float, default=0.0)
    active_time_s: Mapped[float] = mapped_column(Float, default=0.0)
    jerk: Mapped[float] = mapped_column(Float, default=0.0)  # tremor proxy
    # [[t, x, y], ...] normalized centroid path for overlay rendering
    points: Mapped[list] = mapped_column(JSON, default=list)


class PhaseSegment(IdMixin, Base):
    """Procedure phase timeline segment (Subsystem 4)."""

    __tablename__ = "phase_segments"

    procedure_id: Mapped[str] = mapped_column(
        ForeignKey("procedures.id", ondelete="CASCADE"), index=True
    )
    phase: Mapped[str] = mapped_column(String(40), index=True)
    order_idx: Mapped[int] = mapped_column(Integer, default=0)
    t_start_s: Mapped[float] = mapped_column(Float)
    t_end_s: Mapped[float] = mapped_column(Float)
    confidence: Mapped[float] = mapped_column(Float, default=1.0)


class SkillReport(IdMixin, TimestampMixin, Base):
    """Surgical skill assessment (Subsystem 5)."""

    __tablename__ = "skill_reports"

    procedure_id: Mapped[str] = mapped_column(
        ForeignKey("procedures.id", ondelete="CASCADE"), index=True, unique=True
    )
    surgeon_id: Mapped[str] = mapped_column(String(64), default="")
    score: Mapped[float] = mapped_column(Float, default=0.0)  # 0-100
    subscores: Mapped[dict] = mapped_column(JSON, default=dict)
    findings: Mapped[list] = mapped_column(JSON, default=list)


class RiskAssessment(IdMixin, Base):
    """Predicted intra-op risk events over time (Subsystem 7)."""

    __tablename__ = "risk_assessments"

    procedure_id: Mapped[str] = mapped_column(
        ForeignKey("procedures.id", ondelete="CASCADE"), index=True
    )
    t_s: Mapped[float] = mapped_column(Float)
    event_type: Mapped[str] = mapped_column(String(40), index=True)
    probability: Mapped[float] = mapped_column(Float)  # 0-1
    severity: Mapped[str] = mapped_column(String(16), default="medium")
    drivers: Mapped[list] = mapped_column(JSON, default=list)


class CaseEmbedding(IdMixin, Base):
    """Case vector + summary for foundation-model case search (Subsystem 9)."""

    __tablename__ = "case_embeddings"

    procedure_id: Mapped[str] = mapped_column(
        ForeignKey("procedures.id", ondelete="CASCADE"), index=True, unique=True
    )
    provider: Mapped[str] = mapped_column(String(40), default="hashing")
    dim: Mapped[int] = mapped_column(Integer, default=0)
    vector: Mapped[list] = mapped_column(JSON, default=list)
    text_summary: Mapped[str] = mapped_column(Text, default="")
