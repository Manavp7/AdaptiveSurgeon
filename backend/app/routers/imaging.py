"""Real medical-imaging endpoints (M3)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Media, Procedure
from ..services import dicom
from ..storage import get_store

router = APIRouter(tags=["imaging"])

_IMAGING_KINDS = {"ct", "mr", "us"}


@router.get("/procedures/{procedure_id}/imaging")
def list_imaging(procedure_id: str, db: Annotated[Session, Depends(get_db)]) -> dict:
    proc = db.get(Procedure, procedure_id)
    if not proc:
        raise HTTPException(status_code=404, detail="Procedure not found")
    studies = [
        {
            "id": m.id,
            "kind": m.kind,
            "modality": (m.meta or {}).get("modality", m.kind.upper()),
            "depth": (m.meta or {}).get("depth", 1),
            "rows": m.height,
            "cols": m.width,
            "description": (m.meta or {}).get("series_description", ""),
            "filename": m.filename,
        }
        for m in proc.media
        if m.kind in _IMAGING_KINDS
    ]
    return {"procedure_id": procedure_id, "studies": studies}


@router.get("/imaging/{media_id}/volume")
def imaging_volume(media_id: str, db: Annotated[Session, Depends(get_db)]) -> dict:
    media = db.get(Media, media_id)
    if not media or media.kind not in _IMAGING_KINDS:
        raise HTTPException(status_code=404, detail="Imaging study not found")
    path = get_store().open_path(media.uri)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Imaging file missing")
    try:
        vd = dicom.load_volume(path)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=422, detail=f"Cannot read DICOM: {exc}") from exc
    return dicom.volume_to_payload(vd)


@router.get("/imaging/{media_id}/meta")
def imaging_meta(media_id: str, db: Annotated[Session, Depends(get_db)]) -> dict:
    media = db.get(Media, media_id)
    if not media or media.kind not in _IMAGING_KINDS:
        raise HTTPException(status_code=404, detail="Imaging study not found")
    path = get_store().open_path(media.uri)
    return dicom.read_metadata(path)
