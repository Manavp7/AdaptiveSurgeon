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


class ModelPhases(ProcedurePhaseProvider):
    """Trained classifier phase recognition (M4).

    Classifies sampled windows by (time fraction + instruments present), then
    smooths predictions into contiguous, ordered phase segments. Falls back at
    registry level to HeuristicPhases if the model/scikit-learn is unavailable.
    """

    name = "model"

    def __init__(self):
        import joblib  # raises if unavailable

        from ..ml import PHASE_MODEL_PATH
        from ..ml.features import phase_features

        if not PHASE_MODEL_PATH.exists():
            raise FileNotFoundError(f"Phase model not trained: {PHASE_MODEL_PATH}")
        self._bundle = joblib.load(PHASE_MODEL_PATH)
        self._model = self._bundle["model"]
        self._phase_features = phase_features

    def phases(self, procedure_type, duration_s, track_metrics, detection_timeline):
        if duration_s <= 0:
            duration_s = 1.0
        if not detection_timeline:
            return HeuristicPhases().phases(procedure_type, duration_s, track_metrics, detection_timeline)

        # classify each sampled window
        order_index = {p: i for i, p in enumerate(PHASES)}
        preds: list[tuple[float, str]] = []
        rows, times = [], []
        for d in detection_timeline:
            tf = d["t_s"] / duration_s
            rows.append(self._phase_features(tf, d.get("classes", [])))
            times.append(d["t_s"])
        labels = self._model.predict(rows)
        for t, lab in zip(times, labels):
            preds.append((t, str(lab)))

        # enforce monotonic phase order, then merge into contiguous segments
        cleaned: list[tuple[float, str]] = []
        max_order = -1
        for t, lab in preds:
            o = order_index.get(lab, max_order)
            if o < max_order:
                lab = PHASES[max_order]
            else:
                max_order = o
            cleaned.append((t, lab))

        results: list[PhaseResult] = []
        i = 0
        n = len(cleaned)
        while i < n:
            lab = cleaned[i][1]
            start_t = cleaned[i][0]
            j = i
            while j + 1 < n and cleaned[j + 1][1] == lab:
                j += 1
            end_t = cleaned[j][0] if j + 1 >= n else cleaned[j + 1][0]
            results.append(PhaseResult(
                phase=lab, order_idx=order_index.get(lab, len(results)),
                t_start_s=round(start_t, 2), t_end_s=round(max(end_t, start_t), 2),
                confidence=0.8,
            ))
            i = j + 1
        if results:
            results[-1].t_end_s = round(duration_s, 2)
        return results


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
