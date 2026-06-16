"""Background job status endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..services.jobs import registry

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("/{job_id}")
def get_job(job_id: str) -> dict:
    job = registry.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job.to_dict()
