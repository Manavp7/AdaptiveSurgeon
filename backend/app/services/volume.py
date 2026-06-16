"""Synthetic CT volume generator (M5 DICOM-lite).

Generates a small deterministic 3D intensity phantom (liver / gallbladder /
ducts) so the Digital Twin can offer an axial CT slice viewer without real DICOM
tooling. A real build would replace this with pydicom volume ingestion +
windowing + registration (documented in docs/roadmap.md). Returns a base64
uint8 volume for compact transfer.
"""

from __future__ import annotations

import base64
import hashlib

import numpy as np

DEPTH, H, W = 24, 64, 64


def _seed(procedure_id: str) -> int:
    return int.from_bytes(hashlib.sha256(procedure_id.encode()).digest()[:4], "big")


def _ellipsoid(zz, yy, xx, center, radii, value, vol):
    cz, cy, cx = center
    rz, ry, rx = radii
    mask = ((zz - cz) / rz) ** 2 + ((yy - cy) / ry) ** 2 + ((xx - cx) / rx) ** 2 <= 1.0
    vol[mask] = np.maximum(vol[mask], value)


def generate_volume(procedure_id: str) -> dict:
    rng = np.random.RandomState(_seed(procedure_id))
    vol = (rng.rand(DEPTH, H, W) * 25).astype(np.float32)  # soft-tissue noise floor

    zz, yy, xx = np.mgrid[0:DEPTH, 0:H, 0:W]
    # liver (large, mid intensity)
    _ellipsoid(zz, yy, xx, (DEPTH * 0.5, H * 0.42, W * 0.38),
               (DEPTH * 0.42, H * 0.30, W * 0.30), 130, vol)
    # gallbladder (smaller, brighter), with patient variation
    gx = W * (0.62 + 0.05 * (rng.rand() - 0.5))
    _ellipsoid(zz, yy, xx, (DEPTH * 0.52, H * 0.55, gx),
               (DEPTH * 0.18, H * 0.16, W * 0.12), 180, vol)
    # ducts / vessels (bright thin)
    _ellipsoid(zz, yy, xx, (DEPTH * 0.5, H * 0.66, W * 0.5),
               (DEPTH * 0.10, H * 0.30, W * 0.05), 230, vol)

    vol = np.clip(vol, 0, 255).astype(np.uint8)
    return {
        "depth": DEPTH,
        "height": H,
        "width": W,
        "modality": "ct",
        "data_b64": base64.b64encode(vol.tobytes()).decode(),
    }
