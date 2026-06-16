"""In-process background job registry.

Provides async-with-progress UX for long operations (e.g. video analysis)
without requiring Redis/RQ. Jobs run via FastAPI BackgroundTasks; clients poll
``GET /api/jobs/{id}``. Thread-safe for the single-process dev/server setup.

A Redis/RQ-backed implementation can replace this behind the same interface for
horizontal scaling (documented in docs/deployment.md).
"""

from __future__ import annotations

import threading
import time
import uuid
from dataclasses import asdict, dataclass, field
from typing import Literal

JobStatus = Literal["queued", "running", "done", "error"]


@dataclass
class Job:
    id: str
    kind: str
    target_id: str | None = None
    status: JobStatus = "queued"
    progress: float = 0.0  # 0..1
    message: str = ""
    result: dict | None = None
    error: str | None = None
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return asdict(self)


class JobRegistry:
    def __init__(self, max_jobs: int = 500):
        self._jobs: dict[str, Job] = {}
        self._lock = threading.Lock()
        self._max = max_jobs

    def create(self, kind: str, target_id: str | None = None) -> Job:
        job = Job(id=str(uuid.uuid4()), kind=kind, target_id=target_id)
        with self._lock:
            self._jobs[job.id] = job
            self._evict_if_needed()
        return job

    def update(self, job_id: str, **fields) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return
            for k, v in fields.items():
                setattr(job, k, v)
            job.updated_at = time.time()

    def get(self, job_id: str) -> Job | None:
        with self._lock:
            return self._jobs.get(job_id)

    def _evict_if_needed(self) -> None:
        if len(self._jobs) <= self._max:
            return
        # drop oldest finished jobs first
        finished = sorted(
            (j for j in self._jobs.values() if j.status in ("done", "error")),
            key=lambda j: j.created_at,
        )
        for j in finished[: len(self._jobs) - self._max]:
            self._jobs.pop(j.id, None)


registry = JobRegistry()
