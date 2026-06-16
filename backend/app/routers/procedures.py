"""Procedure CRUD + linked-graph detail (Data Platform, Subsystem 1)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Event, Outcome, Patient, Procedure, User
from ..schemas.common import Page
from ..schemas.clinical import (
    EventCreate,
    EventOut,
    OutcomeCreate,
    OutcomeOut,
    ProcedureCreate,
    ProcedureDetailOut,
    ProcedureOut,
)
from ..security import require_role

router = APIRouter(prefix="/procedures", tags=["procedures"])


@router.get("", response_model=Page[ProcedureOut])
def list_procedures(
    db: Annotated[Session, Depends(get_db)],
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> Page:
    q = db.query(Procedure).order_by(Procedure.created_at.desc())
    total = q.count()
    items = q.offset(offset).limit(limit).all()
    return Page(items=items, total=total, limit=limit, offset=offset)


@router.get("/{procedure_id}", response_model=ProcedureDetailOut)
def get_procedure(procedure_id: str, db: Annotated[Session, Depends(get_db)]) -> Procedure:
    proc = db.get(Procedure, procedure_id)
    if not proc:
        raise HTTPException(status_code=404, detail="Procedure not found")
    return proc


@router.post("", response_model=ProcedureOut, status_code=201)
def create_procedure(
    payload: ProcedureCreate,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_role("surgeon"))],
) -> Procedure:
    if not db.get(Patient, payload.patient_id):
        raise HTTPException(status_code=404, detail="Patient not found")
    proc = Procedure(**payload.model_dump())
    db.add(proc)
    db.commit()
    db.refresh(proc)
    return proc


@router.post("/{procedure_id}/events", response_model=EventOut, status_code=201)
def add_event(
    procedure_id: str,
    payload: EventCreate,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_role("surgeon"))],
) -> Event:
    if not db.get(Procedure, procedure_id):
        raise HTTPException(status_code=404, detail="Procedure not found")
    event = Event(procedure_id=procedure_id, **payload.model_dump())
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


@router.put("/{procedure_id}/outcome", response_model=OutcomeOut)
def upsert_outcome(
    procedure_id: str,
    payload: OutcomeCreate,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_role("surgeon"))],
) -> Outcome:
    proc = db.get(Procedure, procedure_id)
    if not proc:
        raise HTTPException(status_code=404, detail="Procedure not found")
    outcome = proc.outcome or Outcome(procedure_id=procedure_id)
    for k, v in payload.model_dump().items():
        setattr(outcome, k, v)
    db.add(outcome)
    db.commit()
    db.refresh(outcome)
    return outcome
