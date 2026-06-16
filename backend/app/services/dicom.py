"""Real DICOM medical-imaging service (M3).

Loads real DICOM studies (single slice, multiframe, or a directory series),
converts pixel data to Hounsfield Units for CT (RescaleSlope/Intercept),
assembles a 3D volume, and exposes metadata + the raw int16 volume for a
PACS-grade client-side viewer (window/level, MPR, HU readout, measurement).

Uses pydicom, which bundles real CT/MR test data so this works fully offline.
"""

from __future__ import annotations

import base64
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

# Size caps so the raw volume transfers compactly to the browser.
MAX_SLICES = 64
MAX_DIM = 256

# Standard CT window presets (center, width) in HU + an MR default.
WINDOW_PRESETS = {
    "Soft tissue": [40, 400],
    "Lung": [-600, 1500],
    "Bone": [400, 1800],
    "Brain": [40, 80],
    "Abdomen": [50, 350],
    "MR default": [None, None],  # filled from data percentiles for non-CT
}


@dataclass
class VolumeData:
    modality: str
    depth: int
    rows: int
    cols: int
    pixel_spacing: list[float]   # [row_mm, col_mm]
    slice_thickness: float
    is_hu: bool
    value_min: float
    value_max: float
    default_window: list[float]  # [center, width]
    volume: np.ndarray = field(repr=False)  # int16 (depth, rows, cols)


def _read_dataset(path: Path):
    import pydicom

    return pydicom.dcmread(str(path))


def _to_volume(ds) -> np.ndarray:
    arr = ds.pixel_array
    if arr.ndim == 2:
        arr = arr[np.newaxis, ...]  # (1, rows, cols)
    return arr.astype(np.float32)


def _downsample(vol: np.ndarray) -> np.ndarray:
    d, r, c = vol.shape
    # slice stride
    if d > MAX_SLICES:
        idx = np.linspace(0, d - 1, MAX_SLICES).round().astype(int)
        vol = vol[idx]
    # in-plane stride
    r, c = vol.shape[1], vol.shape[2]
    rs = max(1, r // MAX_DIM)
    cs = max(1, c // MAX_DIM)
    if rs > 1 or cs > 1:
        vol = vol[:, ::rs, ::cs]
    return vol


def load_volume(path: str | Path) -> VolumeData:
    """Load a DICOM file (single/multiframe) into a HU-aware 3D volume."""
    path = Path(path)
    ds = _read_dataset(path)
    vol = _to_volume(ds)

    modality = str(getattr(ds, "Modality", "OT"))
    slope = float(getattr(ds, "RescaleSlope", 1) or 1)
    intercept = float(getattr(ds, "RescaleIntercept", 0) or 0)
    is_hu = modality == "CT"
    if is_hu:
        vol = vol * slope + intercept

    vol = _downsample(vol)
    vol_i16 = np.clip(vol, -32768, 32767).astype(np.int16)

    ps = getattr(ds, "PixelSpacing", None)
    pixel_spacing = [float(ps[0]), float(ps[1])] if ps else [1.0, 1.0]
    slice_thickness = float(getattr(ds, "SliceThickness", 1.0) or 1.0)

    vmin, vmax = float(vol_i16.min()), float(vol_i16.max())
    if is_hu:
        default_window = [40.0, 400.0]
    else:
        # robust window from percentiles for MR/other
        lo, hi = np.percentile(vol_i16, [2, 98])
        default_window = [float((lo + hi) / 2), float(max(hi - lo, 1))]

    return VolumeData(
        modality=modality,
        depth=int(vol_i16.shape[0]),
        rows=int(vol_i16.shape[1]),
        cols=int(vol_i16.shape[2]),
        pixel_spacing=pixel_spacing,
        slice_thickness=slice_thickness,
        is_hu=is_hu,
        value_min=vmin,
        value_max=vmax,
        default_window=default_window,
        volume=vol_i16,
    )


def volume_to_payload(vd: VolumeData) -> dict:
    """Serialize a volume + metadata for the frontend viewer (raw int16 base64)."""
    presets = {k: v for k, v in WINDOW_PRESETS.items()}
    if not vd.is_hu:
        presets = {"MR default": vd.default_window}
    return {
        "modality": vd.modality,
        "depth": vd.depth,
        "rows": vd.rows,
        "cols": vd.cols,
        "pixel_spacing": vd.pixel_spacing,
        "slice_thickness": vd.slice_thickness,
        "is_hu": vd.is_hu,
        "value_min": vd.value_min,
        "value_max": vd.value_max,
        "default_window": vd.default_window,
        "window_presets": presets,
        "dtype": "int16",
        # row-major (depth, rows, cols) little-endian int16
        "data_b64": base64.b64encode(vd.volume.astype("<i2").tobytes()).decode(),
    }


def read_metadata(path: str | Path) -> dict:
    """Lightweight metadata read for ingestion (no heavy pixel processing)."""
    ds = _read_dataset(Path(path))
    arr = ds.pixel_array
    depth = int(getattr(ds, "NumberOfFrames", 1) or 1) if arr.ndim == 2 else int(arr.shape[0])
    return {
        "modality": str(getattr(ds, "Modality", "OT")),
        "rows": int(getattr(ds, "Rows", arr.shape[-2])),
        "cols": int(getattr(ds, "Columns", arr.shape[-1])),
        "depth": depth,
        "study_description": str(getattr(ds, "StudyDescription", "")),
        "series_description": str(getattr(ds, "SeriesDescription", "")),
    }
