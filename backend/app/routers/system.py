"""System/provider capability reporting.

Reports, for each pluggable provider, the configured implementation and whether
the optional real-model backend is actually importable in this environment — so
the UI can honestly show what is synthetic vs. a real model.
"""

from __future__ import annotations

import importlib.util

from fastapi import APIRouter

from ..config import get_settings
from ..ml import PHASE_MODEL_PATH, RISK_MODEL_PATH

router = APIRouter(prefix="/providers", tags=["system"])
settings = get_settings()


def _importable(module: str) -> bool:
    try:
        return importlib.util.find_spec(module) is not None
    except Exception:  # noqa: BLE001
        return False


@router.get("")
def providers_status() -> dict:
    return {
        "instrument": {
            "configured": settings.instrument_provider,
            "default": "synthetic",
            "real_backend": "ultralytics",
            "real_available": _importable("ultralytics"),
        },
        "anatomy": {
            "configured": settings.anatomy_provider,
            "default": "synthetic",
            "real_backend": "segment_anything",
            "real_available": _importable("segment_anything"),
        },
        "phase": {
            "configured": settings.phase_provider,
            "default": "heuristic",
            "real_backend": "scikit-learn model",
            "real_available": _importable("sklearn") and PHASE_MODEL_PATH.exists(),
        },
        "risk": {
            "configured": settings.risk_provider,
            "default": "rules",
            "real_backend": "scikit-learn model",
            "real_available": _importable("sklearn") and RISK_MODEL_PATH.exists(),
        },
        "copilot": {
            "configured": settings.copilot_provider,
            "default": "rules",
            "real_backend": "LLM",
            "real_available": False,
        },
        "embedding": {
            "configured": settings.embedding_provider,
            "default": "hashing",
            "real_backend": "sentence-transformers",
            "real_available": _importable("sentence_transformers"),
        },
    }
