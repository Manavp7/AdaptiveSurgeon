"""Shared domain constants.

The synthetic video generator renders each instrument in a distinct color, and
the SyntheticDetector finds those same colors. Keeping the palette in one place
guarantees the generator and detector stay consistent.
"""

from __future__ import annotations

# Procedure phases in canonical order (laparoscopic cholecystectomy reference).
PHASES = [
    "access",
    "exposure",
    "dissection",
    "clipping",
    "removal",
    "closure",
]

# Instrument classes rendered/detected in the synthetic pipeline.
# Each: BGR draw color + HSV detection range (OpenCV H in [0,179]).
# Colors chosen to be well separated from the reddish "tissue" background.
INSTRUMENTS: dict[str, dict] = {
    "grasper": {
        "bgr": (255, 60, 0),       # blue
        "hsv_lo": (100, 120, 80),
        "hsv_hi": (130, 255, 255),
    },
    "hook": {
        "bgr": (0, 220, 0),        # green
        "hsv_lo": (45, 120, 80),
        "hsv_hi": (75, 255, 255),
    },
    "scissors": {
        "bgr": (0, 230, 230),      # yellow
        "hsv_lo": (22, 120, 90),
        "hsv_hi": (38, 255, 255),
    },
    "clip_applier": {
        "bgr": (220, 0, 220),      # magenta
        "hsv_lo": (140, 120, 80),
        "hsv_hi": (168, 255, 255),
    },
    "needle_holder": {
        "bgr": (230, 230, 0),      # cyan
        "hsv_lo": (84, 120, 80),
        "hsv_hi": (96, 255, 255),
    },
}

INSTRUMENT_CLASSES = list(INSTRUMENTS.keys())

# Which instruments are typically active in each phase (drives synthetic video
# and the heuristic phase provider).
PHASE_INSTRUMENTS: dict[str, list[str]] = {
    "access": ["grasper"],
    "exposure": ["grasper", "hook"],
    "dissection": ["grasper", "hook"],
    "clipping": ["grasper", "clip_applier"],
    "removal": ["grasper", "scissors"],
    "closure": ["needle_holder"],
}

# Risk event types the risk engine can emit.
RISK_EVENTS = [
    "bleeding",
    "bile_duct_injury",
    "nerve_injury",
    "perforation",
    "leakage",
]
