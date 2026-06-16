"""Media ingestion + streaming (Data Platform, Subsystem 1).

Upload goes through the object-storage abstraction; the same interface accepts
real de-identified hospital media later. Video is served via Starlette's
FileResponse which supports HTTP range requests (needed for browser seeking).
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Annotated

import cv2
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Media, Procedure, User
from ..schemas.clinical import MediaOut
from ..security import require_role
from ..storage import get_store

router = APIRouter(prefix="/media", tags=["media"])

_VIDEO_KINDS = {"video"}


def _probe_video(path: Path) -> dict:
    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        return {}
    fps = cap.get(cv2.CAP_PROP_FPS) or 0.0
    frames = cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0.0
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
    cap.release()
    return {
        "fps": round(fps, 3),
        "duration_s": round(frames / fps, 3) if fps else None,
        "width": w,
        "height": h,
    }


@router.post("", response_model=MediaOut, status_code=201)
async def upload_media(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_role("surgeon"))],
    procedure_id: Annotated[str, Form()],
    kind: Annotated[str, Form()] = "video",
    file: UploadFile = File(...),
) -> Media:
    proc = db.get(Procedure, procedure_id)
    if not proc:
        raise HTTPException(status_code=404, detail="Procedure not found")

    store = get_store()
    suffix = Path(file.filename or "upload.bin").suffix or ".bin"
    data = await file.read()

    media = Media(
        procedure_id=procedure_id, kind=kind, uri="",
        filename=file.filename or f"upload{suffix}",
        content_type=file.content_type or "application/octet-stream",
    )
    db.add(media)
    db.flush()  # get media.id for the storage key

    key = f"procedures/{procedure_id}/{media.id}{suffix}"
    uri = store.save_bytes(key, data)
    media.uri = uri

    if kind in _VIDEO_KINDS:
        meta = _probe_video(store.open_path(uri))
        media.fps = meta.get("fps")
        media.duration_s = meta.get("duration_s")
        media.width = meta.get("width")
        media.height = meta.get("height")

    db.commit()
    db.refresh(media)
    return media


@router.get("/{media_id}/content")
def get_media_content(media_id: str, db: Annotated[Session, Depends(get_db)]):
    media = db.get(Media, media_id)
    if not media:
        raise HTTPException(status_code=404, detail="Media not found")
    store = get_store()
    path = store.open_path(media.uri)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Media file missing")
    return FileResponse(
        path, media_type=media.content_type or "application/octet-stream",
        filename=media.filename or "media",
    )
