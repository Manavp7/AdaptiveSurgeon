"""ProcedurePhaseProvider implementations (Subsystem 4).

Default: HeuristicPhases — builds an ordered phase timeline from canonical phase
proportions, then scores each segment's confidence by how well the instruments
actually detected during that segment match the instruments expected for the
phase. This keeps the timeline connected to the video evidence while remaining
deterministic and offline.
"""

from __future__ import annotations

from ..constants import PHASE_INSTRUMENTS, PHASES
from .base import PhaseResult, ProcedurePhaseProvider

# Typical relative duration of each phase (sums to 1.0).
_PHASE_WEIGHTS = {
    "access": 0.08,
    "exposure": 0.15,
    "dissection": 0.34,
    "clipping": 0.13,
    "removal": 0.20,
    "closure": 0.10,
}


class HeuristicPhases(ProcedurePhaseProvider):
    name = "heuristic"

    def phases(
        self,
        procedure_type: str,
        duration_s: float,
        track_metrics: list[dict],
        detection_timeline: list[dict],
    ) -> list[PhaseResult]:
        if duration_s <= 0:
            duration_s = 1.0

        results: list[PhaseResult] = []
        cursor = 0.0
        for order_idx, phase in enumerate(PHASES):
            seg = _PHASE_WEIGHTS[phase] * duration_s
            t0 = cursor
            t1 = duration_s if order_idx == len(PHASES) - 1 else cursor + seg
            cursor = t1

            conf = self._segment_confidence(phase, t0, t1, detection_timeline)
            results.append(
                PhaseResult(
                    phase=phase,
                    order_idx=order_idx,
                    t_start_s=round(t0, 2),
                    t_end_s=round(t1, 2),
                    confidence=round(conf, 3),
                )
            )
        return results

    @staticmethod
    def _segment_confidence(
        phase: str, t0: float, t1: float, timeline: list[dict]
    ) -> float:
        expected = set(PHASE_INSTRUMENTS.get(phase, []))
        if not expected:
            return 0.5
        frames = [d for d in timeline if t0 <= d["t_s"] < t1]
        if not frames:
            return 0.5
        matches = 0
        total = 0
        for f in frames:
            present = set(f.get("classes", []))
            total += 1
            if present & expected:
                matches += 1
        return 0.5 + 0.5 * (matches / total if total else 0.0)
