"""Surgical approach planning & simulation (M3).

Given the digital-twin anatomy and a proposed instrument approach (entry →
target), this computes the straight-line trajectory, the minimum clearance to
each anatomical structure (especially CRITICAL ones), a safety score, and
warnings. It is a **planning aid only** — not autonomous control. The geometry
operates in the twin's normalized scene-space coordinates.
"""

from __future__ import annotations

import math

# Clearance (scene units) below which an approach is flagged dangerous near a
# critical structure. Illustrative, not a clinical tolerance.
DANGER_CLEARANCE = 0.12
CAUTION_CLEARANCE = 0.28
N_SAMPLES = 48


def _sub(a, b):
    return [a[0] - b[0], a[1] - b[1], a[2] - b[2]]


def _norm(v):
    return math.sqrt(v[0] ** 2 + v[1] ** 2 + v[2] ** 2)


def _point_to_ellipsoid(p, center, radii):
    """Approx signed distance from point to ellipsoid surface (neg = inside)."""
    d = _sub(p, center)
    dist = _norm(d)
    if dist < 1e-9:
        return -min(radii)
    n = math.sqrt(sum((d[i] / radii[i]) ** 2 for i in range(3)))
    # distance to surface along the center ray
    return dist * (1.0 - 1.0 / n) if n > 1e-9 else -min(radii)


def _point_to_segment(p, a, b):
    ab = _sub(b, a)
    ap = _sub(p, a)
    ab2 = sum(x * x for x in ab) or 1e-9
    t = max(0.0, min(1.0, sum(ap[i] * ab[i] for i in range(3)) / ab2))
    proj = [a[i] + t * ab[i] for i in range(3)]
    return _norm(_sub(p, proj))


def _point_to_structure(p, s) -> float:
    g = s.get("geometry", {})
    if g.get("type") == "ellipsoid":
        return _point_to_ellipsoid(p, g["center"], g["radii"])
    if g.get("type") == "cylinder":
        return _point_to_segment(p, g["from"], g["to"]) - float(g.get("radius", 0.05))
    return 1e9


def plan_trajectory(structures: list[dict], entry: list[float], target: list[float]) -> dict:
    samples = [
        [entry[i] + (target[i] - entry[i]) * (k / (N_SAMPLES - 1)) for i in range(3)]
        for k in range(N_SAMPLES)
    ]

    clearances = []
    for s in structures:
        min_c = min(_point_to_structure(p, s) for p in samples)
        clearances.append({
            "structure": s["name"],
            "criticality": s.get("criticality", "safe"),
            "clearance": round(min_c, 4),
            "breach": min_c < DANGER_CLEARANCE,
        })

    critical = [c for c in clearances if c["criticality"] == "critical"]
    min_critical = min((c["clearance"] for c in critical), default=1.0)

    warnings = []
    for c in clearances:
        if c["criticality"] == "critical" and c["clearance"] < DANGER_CLEARANCE:
            warnings.append(
                f"DANGER: trajectory passes within {c['clearance']:.2f} of critical "
                f"{c['structure'].replace('_', ' ')}."
            )
        elif c["criticality"] == "critical" and c["clearance"] < CAUTION_CLEARANCE:
            warnings.append(
                f"Caution: limited clearance ({c['clearance']:.2f}) to "
                f"{c['structure'].replace('_', ' ')}."
            )

    # safety score 0-100: scaled by min clearance to critical structures
    score = max(0.0, min(100.0, (min_critical / CAUTION_CLEARANCE) * 100.0))
    safe = min_critical >= DANGER_CLEARANCE
    if not warnings:
        warnings.append("Approach maintains safe clearance from all critical structures.")

    return {
        "entry": [round(x, 4) for x in entry],
        "target": [round(x, 4) for x in target],
        "trajectory": [[round(x, 4) for x in p] for p in samples],
        "clearances": sorted(clearances, key=lambda c: c["clearance"]),
        "min_critical_clearance": round(min_critical, 4),
        "safety_score": round(score, 1),
        "safe": safe,
        "warnings": warnings,
        "disclaimer": "Planning aid only — not autonomous control; advisory, not validated.",
    }
