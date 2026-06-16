"""AdaptiveSurgeon API — application entrypoint.

A coherent Surgical Intelligence OS: one workflow connects the Data Platform,
Video Intelligence, Procedure Timeline, Skill, Risk, Copilot, Digital Twin and
Foundation/Case-search subsystems. Advisory-only research prototype.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import __version__
from .config import get_settings
from .db import init_db

settings = get_settings()

app = FastAPI(
    title="AdaptiveSurgeon API",
    version=__version__,
    description=(
        "Surgical Intelligence Operating System (research prototype, ADVISORY "
        "ONLY — not a medical device)."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1):\d+",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def _startup() -> None:
    init_db()


@app.get("/health", tags=["system"])
def health() -> dict:
    return {
        "status": "ok",
        "app": settings.app_name,
        "version": __version__,
        "environment": settings.environment,
        "providers": {
            "instrument": settings.instrument_provider,
            "anatomy": settings.anatomy_provider,
            "phase": settings.phase_provider,
            "risk": settings.risk_provider,
            "copilot": settings.copilot_provider,
            "embedding": settings.embedding_provider,
        },
    }


def _register_routers() -> None:
    """Include API routers. Imported lazily so partial builds still boot."""
    from .routers import (
        analysis,
        auth,
        foundation,
        jobs,
        media,
        patients,
        procedures,
        twin,
    )

    p = settings.api_prefix
    app.include_router(auth.router, prefix=p)
    app.include_router(patients.router, prefix=p)
    app.include_router(procedures.router, prefix=p)
    app.include_router(media.router, prefix=p)
    app.include_router(analysis.router, prefix=p)
    app.include_router(jobs.router, prefix=p)
    app.include_router(twin.router, prefix=p)
    app.include_router(foundation.router, prefix=p)


_register_routers()
