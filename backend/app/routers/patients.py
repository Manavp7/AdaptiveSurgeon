"""Patient CRUD (Data Platform, Subsystem 1)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Patient, User
from ..schemas.clinical import PatientCreate, PatientOut
from ..schemas.common import Page
from ..security import require_role

router = APIRouter(prefix="/patients", tags=["patients"])


@router.get("", response_model=Page[PatientOut])
def list_patients(
    db: Annotated[Session, Depends(get_db)],
    limit: int = Query(200, ge=1, le=1000),
    offset: int = Query(0, ge=0),
) -> Page:
    q = db.query(Patient).order_by(Patient.created_at.desc())
    total = q.count()
    items = q.offset(offset).limit(limit).all()
    return Page(items=items, total=total, limit=limit, offset=offset)


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
    from ..security_deid import pseudonymize

    patient = Patient(**payload.model_dump())
    patient.mrn_hash = pseudonymize(patient.external_mrn)
    db.add(patient)
    db.commit()
    db.refresh(patient)
    return patient
