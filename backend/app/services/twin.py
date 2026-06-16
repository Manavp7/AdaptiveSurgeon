"""Digital Twin service (Subsystem 8).

Builds a structured 3D anatomy description from (synthetic) pre-op imaging
metadata that the frontend renders with Three.js, plus an expected-vs-actual
comparison derived from intra-op anatomy segmentation. The geometry is simple
parametric primitives so it renders anywhere without DICOM tooling; a real
build would substitute volume-rendered meshes from CT/MRI.
"""

from __future__ import annotations

import hashlib

# Canonical expected anatomy for the reference procedure. Positions in a
# normalized scene space; criticality drives the safe/caution/critical color.
_BASE_STRUCTURES = [
    {"name": "liver", "criticality": "safe", "color": "#2e9e5b",
     "geometry": {"type": "ellipsoid", "center": [-0.6, 0.3, 0.0], "radii": [0.9, 0.5, 0.6]}},
    {"name": "gallbladder", "criticality": "caution", "color": "#e0a800",
     "geometry": {"type": "ellipsoid", "center": [0.5, -0.1, 0.2], "radii": [0.32, 0.5, 0.32]}},
    {"name": "cystic_duct", "criticality": "critical", "color": "#d83a3a",
     "geometry": {"type": "cylinder", "from": [0.35, -0.45, 0.2], "to": [0.05, -0.8, 0.0], "radius": 0.06}},
    {"name": "common_bile_duct", "criticality": "critical", "color": "#d83a3a",
     "geometry": {"type": "cylinder", "from": [0.05, -0.8, 0.0], "to": [-0.1, -1.3, -0.1], "radius": 0.08}},
    {"name": "cystic_artery", "criticality": "critical", "color": "#b5179e",
     "geometry": {"type": "cylinder", "from": [0.4, -0.35, 0.3], "to": [0.15, -0.7, 0.15], "radius": 0.05}},
]


def _rng_from_seed(seed: str) -> float:
    """Deterministic [0,1) from a string seed (no global RNG state)."""
    h = hashlib.sha256(seed.encode()).digest()
    return int.from_bytes(h[:4], "big") / 0xFFFFFFFF


def build_twin(procedure_id: str, procedure_type: str, patient_history: dict) -> dict:
    """Return {source_modality, structures, expected_vs_actual, mesh_uri}."""
    structures = [dict(s) for s in _BASE_STRUCTURES]

    # Inject patient-specific anatomical variants deterministically so the
    # "expected vs actual" panel has meaningful, reproducible content.
    diffs: list[dict] = []
    r = _rng_from_seed(procedure_id)
    if r > 0.5:
        diffs.append({
            "structure": "cystic_artery",
            "type": "anatomical_variant",
            "detail": "Anterior cystic artery variant detected vs expected posterior course.",
            "severity": "high",
        })
    if r > 0.75 or "diabetes" in str(patient_history).lower():
        diffs.append({
            "structure": "gallbladder",
            "type": "morphology",
            "detail": "Thickened, contracted gallbladder wall (chronic cholecystitis).",
            "severity": "medium",
        })
    if not diffs:
        diffs.append({
            "structure": "common_bile_duct",
            "type": "match",
            "detail": "Intra-op anatomy matches expected pre-op model.",
            "severity": "info",
        })

    return {
        "source_modality": "ct",
        "structures": structures,
        "expected_vs_actual": diffs,
        "mesh_uri": None,
    }
