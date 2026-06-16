"""Schemas for the clinical data platform (Subsystem 1)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# --- Patient ---
class PatientCreate(BaseModel):
    external_mrn: str
    display_name: str = ""
    age: int | None = None
    sex: str | None = None
    bmi: float | None = None
    history: dict = Field(default_factory=dict)
    consent_obtained: bool = False
    consent_reference: str = ""


class PatientOut(ORMModel):
    id: str
    external_mrn: str
    mrn_hash: str
    display_name: str
    age: int | None
    sex: str | None
    bmi: float | None
    history: dict
    consent_obtained: bool
    consent_reference: str
    created_at: datetime


# --- Procedure ---
class ProcedureCreate(BaseModel):
    patient_id: str
    procedure_type: str
    surgeon_id: str = ""
    surgeon_name: str = ""
    started_at: str | None = None
    ended_at: str | None = None
    notes: str = ""


class ProcedureOut(ORMModel):
    id: str
    patient_id: str
    procedure_type: str
    surgeon_id: str
    surgeon_name: str
    started_at: str | None
    ended_at: str | None
    status: str
    notes: str
    created_at: datetime


class MediaOut(ORMModel):
    id: str
    procedure_id: str
    kind: str
    uri: str
    filename: str
    content_type: str
    duration_s: float | None
    fps: float | None
    width: int | None
    height: int | None
    meta: dict


class EventOut(ORMModel):
    id: str
    procedure_id: str
    kind: str
    label: str
    t_start_s: float
    t_end_s: float | None
    severity: str
    payload: dict


class EventCreate(BaseModel):
    kind: str = "annotation"
    label: str
    t_start_s: float = 0.0
    t_end_s: float | None = None
    severity: str = "info"
    payload: dict = Field(default_factory=dict)


class OutcomeCreate(BaseModel):
    discharge_summary: str = ""
    complications: list = Field(default_factory=list)
    length_of_stay_days: float | None = None
    readmission_30d: bool = False
    mortality: bool = False
    notes: str = ""


class OutcomeOut(ORMModel):
    id: str
    procedure_id: str
    discharge_summary: str
    complications: list
    length_of_stay_days: float | None
    readmission_30d: bool
    mortality: bool
    notes: str


class ProcedureDetailOut(ProcedureOut):
    """Procedure plus its linked graph (media, events, outcome)."""

    patient: PatientOut
    media: list[MediaOut] = []
    events: list[EventOut] = []
    outcome: OutcomeOut | None = None
