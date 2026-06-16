"""Shared feature engineering for the trainable risk & phase models.

Keeping feature construction in one place guarantees the training scripts and
the inference-time providers produce identical vectors.
"""

from __future__ import annotations

from ..constants import INSTRUMENT_CLASSES, PHASES, RISK_EVENTS


def risk_features(phase: str, event_type: str, baseline: float, motion: float, tremor: float) -> list[float]:
    """Feature vector for a (phase, event) risk prediction."""
    vec: list[float] = []
    vec += [1.0 if phase == p else 0.0 for p in PHASES]          # phase one-hot
    vec += [1.0 if event_type == e else 0.0 for e in RISK_EVENTS]  # event one-hot
    vec += [baseline, motion, tremor]
    return vec


RISK_FEATURE_DIM = len(PHASES) + len(RISK_EVENTS) + 3


def phase_features(time_fraction: float, present: list[str]) -> list[float]:
    """Feature vector for window-level phase classification."""
    present_set = set(present)
    vec = [time_fraction]
    vec += [1.0 if c in present_set else 0.0 for c in INSTRUMENT_CLASSES]
    return vec


PHASE_FEATURE_DIM = 1 + len(INSTRUMENT_CLASSES)
