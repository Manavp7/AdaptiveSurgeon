"""Core clinical data-platform models (Subsystem 1).

Chain mirrors the vision exactly:

    Patient -> Procedure -> Media(Video/Imaging) -> Event -> Outcome

JSON columns keep payloads flexible so real de-identified hospital data can be
ingested later without schema churn.
"""

from __future__ import annotations

from sqlalchemy import JSON, Boolean, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..db import Base
from .base import IdMixin, TimestampMixin


class Patient(IdMixin, TimestampMixin, Base):
    __tablename__ = "patients"

    # external_mrn is intended to be a hashed/de-identified reference.
    external_mrn: Mapped[str] = mapped_column(String(64), index=True)
    # Pseudonymized token of the MRN (PHI de-id pathway).
    mrn_hash: Mapped[str] = mapped_column(String(32), default="", index=True)
    display_name: Mapped[str] = mapped_column(String(120), default="")
    age: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sex: Mapped[str | None] = mapped_column(String(16), nullable=True)
    bmi: Mapped[float | None] = mapped_column(Float, nullable=True)
    history: Mapped[dict] = mapped_column(JSON, default=dict)
    # Consent tracking (prerequisite for any real-data use).
    consent_obtained: Mapped[bool] = mapped_column(Boolean, default=False)
    consent_reference: Mapped[str] = mapped_column(String(120), default="")

    procedures: Mapped[list["Procedure"]] = relationship(
        back_populates="patient", cascade="all, delete-orphan"
    )


class Procedure(IdMixin, TimestampMixin, Base):
    __tablename__ = "procedures"

    patient_id: Mapped[str] = mapped_column(
        ForeignKey("patients.id", ondelete="CASCADE"), index=True
    )
    procedure_type: Mapped[str] = mapped_column(String(80), index=True)
    surgeon_id: Mapped[str] = mapped_column(String(64), default="")
    surgeon_name: Mapped[str] = mapped_column(String(120), default="")
    started_at: Mapped[str | None] = mapped_column(String(40), nullable=True)
    ended_at: Mapped[str | None] = mapped_column(String(40), nullable=True)
    # registered | processing | analyzed | failed
    status: Mapped[str] = mapped_column(String(24), default="registered")
    notes: Mapped[str] = mapped_column(Text, default="")

    patient: Mapped["Patient"] = relationship(back_populates="procedures")
    media: Mapped[list["Media"]] = relationship(
        back_populates="procedure", cascade="all, delete-orphan"
    )
    events: Mapped[list["Event"]] = relationship(
        back_populates="procedure", cascade="all, delete-orphan"
    )
    outcome: Mapped["Outcome | None"] = relationship(
        back_populates="procedure", uselist=False, cascade="all, delete-orphan"
    )


class Media(IdMixin, TimestampMixin, Base):
    __tablename__ = "media"

    procedure_id: Mapped[str] = mapped_column(
        ForeignKey("procedures.id", ondelete="CASCADE"), index=True
    )
    # video | audio | ct | mri | us | ecg | report
    kind: Mapped[str] = mapped_column(String(24), index=True)
    uri: Mapped[str] = mapped_column(String(512))
    filename: Mapped[str] = mapped_column(String(255), default="")
    content_type: Mapped[str] = mapped_column(String(80), default="")
    duration_s: Mapped[float | None] = mapped_column(Float, nullable=True)
    fps: Mapped[float | None] = mapped_column(Float, nullable=True)
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    meta: Mapped[dict] = mapped_column(JSON, default=dict)

    procedure: Mapped["Procedure"] = relationship(back_populates="media")


class Event(IdMixin, TimestampMixin, Base):
    __tablename__ = "events"

    procedure_id: Mapped[str] = mapped_column(
        ForeignKey("procedures.id", ondelete="CASCADE"), index=True
    )
    # phase | advisory | risk | complication | annotation
    kind: Mapped[str] = mapped_column(String(24), index=True)
    label: Mapped[str] = mapped_column(String(120))
    t_start_s: Mapped[float] = mapped_column(Float, default=0.0)
    t_end_s: Mapped[float | None] = mapped_column(Float, nullable=True)
    # info | low | medium | high | critical
    severity: Mapped[str] = mapped_column(String(16), default="info")
    payload: Mapped[dict] = mapped_column(JSON, default=dict)

    procedure: Mapped["Procedure"] = relationship(back_populates="events")


class Outcome(IdMixin, TimestampMixin, Base):
    __tablename__ = "outcomes"

    procedure_id: Mapped[str] = mapped_column(
        ForeignKey("procedures.id", ondelete="CASCADE"), index=True, unique=True
    )
    discharge_summary: Mapped[str] = mapped_column(Text, default="")
    complications: Mapped[list] = mapped_column(JSON, default=list)
    length_of_stay_days: Mapped[float | None] = mapped_column(Float, nullable=True)
    readmission_30d: Mapped[bool] = mapped_column(Boolean, default=False)
    mortality: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[str] = mapped_column(Text, default="")

    procedure: Mapped["Procedure"] = relationship(back_populates="outcome")
