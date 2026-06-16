"""AnatomySegmentationProvider implementations.

Default: SyntheticAnatomy — returns deterministic anatomical regions with
safe/caution/critical labels for the overlay legend (Green/Yellow/Red per the
vision). Optional: SamSegmenter scaffold for a real SAM model later.
"""

from __future__ import annotations

import numpy as np

from .base import AnatomySegmentationProvider, MaskResult

# Static reference layout (normalized coords). In the real system this comes
# from a trained segmentation model; here it provides a consistent overlay.
_STRUCTURES = [
    ("liver", "safe", [[0.05, 0.05], [0.55, 0.05], [0.5, 0.4], [0.05, 0.45]]),
    ("gallbladder", "caution", [[0.55, 0.35], [0.78, 0.32], [0.8, 0.6], [0.58, 0.62]]),
    ("bile_duct", "critical", [[0.45, 0.55], [0.6, 0.58], [0.58, 0.78], [0.43, 0.72]]),
    ("cystic_artery", "critical", [[0.62, 0.6], [0.74, 0.63], [0.72, 0.8], [0.6, 0.76]]),
    ("bowel", "caution", [[0.1, 0.7], [0.4, 0.72], [0.38, 0.95], [0.08, 0.93]]),
]


class SyntheticAnatomy(AnatomySegmentationProvider):
    name = "synthetic"

    def segment(self, frame: np.ndarray, t_s: float) -> list[MaskResult]:
        return [
            MaskResult(
                class_name=name,
                criticality=crit,
                confidence=0.6,
                polygon=poly,
            )
            for name, crit, poly in _STRUCTURES
        ]


class SamSegmenter(AnatomySegmentationProvider):
    """Optional Segment Anything scaffold (drop-in real model)."""

    name = "sam"

    def __init__(self, checkpoint: str | None = None):
        from segment_anything import sam_model_registry  # noqa: F401

        raise NotImplementedError(
            "SAM integration is a roadmap item; enable by implementing segment()."
        )

    def segment(self, frame: np.ndarray, t_s: float) -> list[MaskResult]:
        raise NotImplementedError
