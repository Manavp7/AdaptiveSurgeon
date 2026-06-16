"""Tests for the real DICOM imaging pipeline (M3)."""

from __future__ import annotations

import base64

import numpy as np
from pydicom.data import get_testdata_file

from app.services import dicom


def test_ct_loads_with_hounsfield_units():
    vd = dicom.load_volume(get_testdata_file("CT_small.dcm"))
    assert vd.modality == "CT"
    assert vd.is_hu
    # real CT HU spans negative (air) to positive (bone) values
    assert vd.value_min < -500 and vd.value_max > 500
    assert vd.pixel_spacing[0] > 0


def test_mr_volume_is_3d():
    vd = dicom.load_volume(get_testdata_file("emri_small.dcm"))
    assert vd.modality == "MR"
    assert vd.depth == 10
    assert not vd.is_hu


def test_volume_payload_roundtrip():
    vd = dicom.load_volume(get_testdata_file("CT_small.dcm"))
    payload = dicom.volume_to_payload(vd)
    raw = base64.b64decode(payload["data_b64"])
    arr = np.frombuffer(raw, dtype="<i2")
    assert arr.size == vd.depth * vd.rows * vd.cols
    assert "window_presets" in payload


def test_imaging_endpoints(client):
    procs = client.get("/api/procedures").json()["items"]
    pid = procs[0]["id"]
    studies = client.get(f"/api/procedures/{pid}/imaging").json()["studies"]
    assert any(s["kind"] == "ct" for s in studies)
    assert any(s["kind"] == "mr" and s["depth"] == 10 for s in studies)
    ct = next(s for s in studies if s["kind"] == "ct")
    vol = client.get(f"/api/imaging/{ct['id']}/volume").json()
    assert vol["is_hu"] is True
    assert vol["modality"] == "CT"
