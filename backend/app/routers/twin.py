"""Digital Twin endpoints (Subsystem 8)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import DigitalTwin, Procedure
from ..schemas.twin import DigitalTwinOut
from ..services import twin as twin_service
from ..services import volume as volume_service

router = APIRouter(prefix="/procedures", tags=["digital-twin"])


@router.get("/{procedure_id}/twin/volume")
def get_twin_volume(procedure_id: str, db: Annotated[Session, Depends(get_db)]) -> dict:
    proc = db.get(Procedure, procedure_id)
    if not proc:
        raise HTTPException(status_code=404, detail="Procedure not found")
    return volume_service.generate_volume(procedure_id)


@router.get("/{procedure_id}/twin", response_model=DigitalTwinOut)
def get_twin(procedure_id: str, db: Annotated[Session, Depends(get_db)]) -> DigitalTwin:
    proc = db.get(Procedure, procedure_id)
    if not proc:
        raise HTTPException(status_code=404, detail="Procedure not found")

    twin = db.query(DigitalTwin).filter_by(procedure_id=procedure_id).first()
    if twin is None:
        # Build on demand if analysis hasn't produced one yet.
        data = twin_service.build_twin(
            proc.id, proc.procedure_type, proc.patient.history if proc.patient else {}
        )
        twin = DigitalTwin(
            procedure_id=proc.id, source_modality=data["source_modality"],
            structures=data["structures"], mesh_uri=data["mesh_uri"],
            expected_vs_actual=data["expected_vs_actual"],
        )
        db.add(twin)
        db.commit()
        db.refresh(twin)
    return twin
