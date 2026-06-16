"""Provider-level unit tests (deterministic, offline)."""

from __future__ import annotations

import numpy as np

from app.providers import get_embedding_provider, get_instrument_provider
from app.seed.sample_video import render_surgical_video
from app.services.skill import compute_skill
from app.services.tracking import CentroidTracker
from app.services.video_intel import analyze_video


def test_embedding_deterministic_and_normalized():
    emb = get_embedding_provider()
    v1 = emb.embed("cholecystectomy bleeding dissection")
    v2 = emb.embed("cholecystectomy bleeding dissection")
    assert v1 == v2  # process-independent stable hashing
    norm = sum(x * x for x in v1) ** 0.5
    assert abs(norm - 1.0) < 1e-6


def test_synthetic_detector_finds_instruments():
    det = get_instrument_provider()
    assert det.name == "synthetic"
    render_surgical_video("/tmp/_t_det.mp4", seed=1, skill=0.7, duration_s=6, fps=12)
    va = analyze_video("/tmp/_t_det.mp4", det, sample_fps=5)
    classes = {d.class_name for fd in va.frames for d in fd.detections}
    # multiple distinct instrument classes detected
    assert len(classes) >= 3


def _skill_for(skill: float) -> float:
    det = get_instrument_provider()
    p = f"/tmp/_t_skill_{int(skill*100)}.mp4"
    render_surgical_video(p, seed=7, skill=skill, duration_s=10, fps=12)
    va = analyze_video(p, det, sample_fps=5)
    diag = (va.width**2 + va.height**2) ** 0.5
    tr = CentroidTracker(9000.0, diag)
    timeline = []
    for fd in va.frames:
        tr.update(fd.t_s, fd.detections)
        timeline.append({"t_s": fd.t_s, "classes": [d.class_name for d in fd.detections]})
    tm = tr.metrics()
    phases = [{"phase": "dissection", "confidence": 1.0, "t_start_s": 0, "t_end_s": va.duration_s}]
    return compute_skill(tm, phases, va.duration_s, va.camera_motion).score


def test_skill_is_monotonic_in_technique():
    expert = _skill_for(0.9)
    intermediate = _skill_for(0.5)
    novice = _skill_for(0.2)
    assert expert > intermediate > novice
