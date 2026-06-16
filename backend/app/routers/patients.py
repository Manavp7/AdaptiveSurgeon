"""Patient CRUD (Data Platform, Subsystem 1)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Patient, User
from ..schemas.clinical import PatientCreate, PatientOut
from ..security import require_role

router = APIRouter(prefix="/patients", tags=["patients"])


@router.get("", response_model=list[PatientOut])
def list_patients(db: Annotated[Session, Depends(get_db)]) -> list[Patient]:
    return db.query(Patient).order_by(Patient.created_at.desc()).all()


@router.get("/{patient_id}", response_model=PatientOut)
def get_patient(patient_id: str, db: Annotated[Session, Depends(get_db)]) -> Patient:
    patient = db.get(Patient, patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    return patient


@router.post("", response_model=PatientOut, status_code=201)
def create_patient(
    payload: PatientCreate,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_role("surgeon"))],
) -> Patient:
    patient = Patient(**payload.model_dump())
    db.add(patient)
    db.commit()
    db.refresh(patient)
    return patient
