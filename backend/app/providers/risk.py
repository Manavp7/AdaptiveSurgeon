"""RiskAssessmentProvider implementations (Subsystem 7).

Default: RuleRisk — assembles features (phase, instrument speed/jerk, idle) and
emits a deterministic risk timeline. The clinical priors are illustrative only
(ADVISORY ONLY, not validated). A trained multimodal model can replace this by
implementing the same ``assess(features)`` interface.
"""

from __future__ import annotations

import math

from ..constants import RISK_EVENTS
from .base import RiskAssessmentProvider, RiskResult

# Per-phase baseline susceptibility for each risk event (illustrative).
_PHASE_RISK = {
    "access": {"perforation": 0.15, "bleeding": 0.05},
    "exposure": {"bleeding": 0.1},
    "dissection": {"bile_duct_injury": 0.25, "bleeding": 0.2, "nerve_injury": 0.12},
    "clipping": {"bile_duct_injury": 0.3, "bleeding": 0.15},
    "removal": {"bleeding": 0.18, "perforation": 0.1},
    "closure": {"leakage": 0.15},
}


def _sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))


def _severity(p: float) -> str:
    if p >= 0.66:
        return "high"
    if p >= 0.4:
        return "medium"
    return "low"


class RuleRisk(RiskAssessmentProvider):
    name = "rules"

    def assess(self, features: dict) -> list[RiskResult]:
        phases = features.get("phases", [])
        # motion intensity in [0,1]: faster/jerkier motion => higher modifier
        motion = float(features.get("motion_intensity", 0.3))
        tremor = float(features.get("tremor", 0.3))
        results: list[RiskResult] = []

        for ph in phases:
            phase = ph["phase"]
            mid_t = (ph["t_start_s"] + ph["t_end_s"]) / 2.0
            base = _PHASE_RISK.get(phase, {})
            for event, b in base.items():
                # logistic combination of baseline + motion + tremor drivers
                logit = -1.4 + 4.0 * b + 1.6 * motion + 1.2 * tremor
                p = round(_sigmoid(logit), 3)
                drivers = [f"phase:{phase}"]
                if motion > 0.5:
                    drivers.append("elevated instrument speed")
                if tremor > 0.5:
                    drivers.append("instrument tremor")
                if event in ("bile_duct_injury",) and phase in ("dissection", "clipping"):
                    drivers.append("critical structure proximity")
                results.append(
                    RiskResult(
                        t_s=round(mid_t, 2),
                        event_type=event,
                        probability=p,
                        severity=_severity(p),
                        drivers=drivers,
                    )
                )
        # keep only meaningful events, sorted by time then probability
        results = [r for r in results if r.event_type in RISK_EVENTS]
        results.sort(key=lambda r: (r.t_s, -r.probability))
        return results
