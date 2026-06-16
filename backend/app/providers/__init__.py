"""Provider registry — selects implementations by configuration.

Synthetic/heuristic providers are the defaults and always available offline.
Optional real-model providers are attempted only when configured; if their
dependencies are missing or fail to load, we log a warning and fall back to the
synthetic provider so the platform never breaks offline.
"""

from __future__ import annotations

import logging

from ..config import get_settings
from .anatomy import SyntheticAnatomy
from .base import (
    AnatomySegmentationProvider,
    CopilotProvider,
    EmbeddingProvider,
    InstrumentDetectionProvider,
    ProcedurePhaseProvider,
    RiskAssessmentProvider,
)
from .copilot import RuleCopilot
from .embedding import HashingTfidfEmbedder
from .instrument import SyntheticDetector
from .phase import HeuristicPhases
from .risk import RuleRisk

log = logging.getLogger("adaptivesurgeon.providers")
settings = get_settings()


def _try(real_factory, fallback_factory, name: str):
    try:
        provider = real_factory()
        log.info("Loaded real provider: %s", name)
        return provider
    except Exception as exc:  # offline-safe: never break
        log.warning(
            "Provider '%s' unavailable (%s); using synthetic fallback.", name, exc
        )
        return fallback_factory()


def get_instrument_provider() -> InstrumentDetectionProvider:
    if settings.instrument_provider == "yolo":
        from .instrument import YoloDetector

        return _try(YoloDetector, SyntheticDetector, "yolo")
    return SyntheticDetector()


def get_anatomy_provider() -> AnatomySegmentationProvider:
    if settings.anatomy_provider == "sam":
        from .anatomy import SamSegmenter

        return _try(SamSegmenter, SyntheticAnatomy, "sam")
    return SyntheticAnatomy()


def get_phase_provider() -> ProcedurePhaseProvider:
    if settings.phase_provider == "model":
        from .phase import ModelPhases

        return _try(ModelPhases, HeuristicPhases, "phase_model")
    return HeuristicPhases()


def get_risk_provider() -> RiskAssessmentProvider:
    if settings.risk_provider == "model":
        from .risk import ModelRisk

        return _try(ModelRisk, RuleRisk, "risk_model")
    return RuleRisk()


def get_copilot_provider() -> CopilotProvider:
    return RuleCopilot()


def get_embedding_provider() -> EmbeddingProvider:
    if settings.embedding_provider == "sentence_transformer":
        from .embedding import SentenceTransformerEmbedder

        return _try(
            SentenceTransformerEmbedder, HashingTfidfEmbedder, "sentence_transformer"
        )
    return HashingTfidfEmbedder()


__all__ = [
    "get_instrument_provider",
    "get_anatomy_provider",
    "get_phase_provider",
    "get_risk_provider",
    "get_copilot_provider",
    "get_embedding_provider",
]
