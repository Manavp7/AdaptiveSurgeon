"""Stable provider interfaces — the seam that makes AdaptiveSurgeon an OS.

Every intelligence module is accessed through one of these ABCs. The default
implementations are synthetic/heuristic and run fully offline. Real models
(YOLO, SAM, temporal transformers, trained risk models, LLMs, sentence
embeddings) are drop-in replacements that implement the same interface and are
selected via configuration — no architectural change required.
"""

from __future__ import annotations

import abc
from dataclasses import dataclass, field

import numpy as np


# --- shared result types ---
@dataclass
class DetectionResult:
    class_name: str
    confidence: float
    # normalized [0,1] bbox (x, y = top-left)
    x: float
    y: float
    w: float
    h: float


@dataclass
class MaskResult:
    class_name: str
    criticality: str  # safe | caution | critical
    confidence: float
    # normalized polygon [[x,y], ...] for overlay rendering
    polygon: list[list[float]]


@dataclass
class PhaseResult:
    phase: str
    order_idx: int
    t_start_s: float
    t_end_s: float
    confidence: float


@dataclass
class RiskResult:
    t_s: float
    event_type: str
    probability: float
    severity: str
    drivers: list[str] = field(default_factory=list)


@dataclass
class AdvisoryResult:
    t_start_s: float
    label: str
    severity: str
    t_end_s: float | None = None
    payload: dict = field(default_factory=dict)


# --- provider interfaces ---
class InstrumentDetectionProvider(abc.ABC):
    name: str = "base"

    @abc.abstractmethod
    def detect(self, frame: np.ndarray, t_s: float) -> list[DetectionResult]:
        """Detect surgical instruments in a single BGR frame."""


class AnatomySegmentationProvider(abc.ABC):
    name: str = "base"

    @abc.abstractmethod
    def segment(self, frame: np.ndarray, t_s: float) -> list[MaskResult]:
        """Segment anatomical structures with safe/caution/critical labels."""


class ProcedurePhaseProvider(abc.ABC):
    name: str = "base"

    @abc.abstractmethod
    def phases(
        self,
        procedure_type: str,
        duration_s: float,
        track_metrics: list[dict],
        detection_timeline: list[dict],
    ) -> list[PhaseResult]:
        """Produce an ordered phase timeline for the procedure."""


class RiskAssessmentProvider(abc.ABC):
    name: str = "base"

    @abc.abstractmethod
    def assess(self, features: dict) -> list[RiskResult]:
        """Predict intra-op risk events over time from assembled features."""


class CopilotProvider(abc.ABC):
    name: str = "base"

    @abc.abstractmethod
    def advise(self, context: dict) -> list[AdvisoryResult]:
        """Produce advisory-only guidance from current surgical context."""


class EmbeddingProvider(abc.ABC):
    name: str = "base"
    dim: int = 0

    @abc.abstractmethod
    def embed(self, text: str) -> list[float]:
        """Embed a case summary into a fixed-length vector."""
