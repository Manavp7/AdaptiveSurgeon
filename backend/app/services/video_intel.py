"""Video Intelligence frame processing (Subsystem 2).

Reads a video from object storage, samples frames at a configured rate, runs the
configured InstrumentDetectionProvider on each, and returns per-frame detections
plus a per-frame "camera motion" estimate (mean absolute frame difference) used
by the skill engine for camera-stability scoring.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import cv2
import numpy as np

from ..providers.base import DetectionResult, InstrumentDetectionProvider


@dataclass
class FrameDetections:
    frame_idx: int
    t_s: float
    detections: list[DetectionResult] = field(default_factory=list)


@dataclass
class VideoAnalysis:
    width: int
    height: int
    fps: float
    duration_s: float
    frames: list[FrameDetections]
    camera_motion: float  # mean global motion across sampled frames [0,1]
    representative_frame: np.ndarray | None = None  # mid-procedure frame (BGR)


def analyze_video(
    path: str | Path,
    detector: InstrumentDetectionProvider,
    sample_fps: float = 5.0,
) -> VideoAnalysis:
    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        raise FileNotFoundError(f"Cannot open video: {path}")

    src_fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
    step = max(1, int(round(src_fps / max(sample_fps, 0.1))))

    frames: list[FrameDetections] = []
    motions: list[float] = []
    prev_small: np.ndarray | None = None
    mid_frame_idx = (total // 2) if total else 0
    representative: np.ndarray | None = None

    idx = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        if idx % step == 0:
            t_s = idx / src_fps
            dets = detector.detect(frame, t_s)
            frames.append(FrameDetections(frame_idx=idx, t_s=round(t_s, 3), detections=dets))

            small = cv2.resize(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY), (64, 64))
            if prev_small is not None:
                motions.append(float(np.mean(np.abs(small.astype(np.int16) - prev_small.astype(np.int16))) / 255.0))
            prev_small = small
        if representative is None and idx >= mid_frame_idx:
            representative = frame.copy()
        idx += 1
    cap.release()
    if representative is None and frames:
        representative = None  # no frame captured (empty video)

    duration_s = (total / src_fps) if total else (frames[-1].t_s if frames else 0.0)
    camera_motion = float(np.mean(motions)) if motions else 0.0
    return VideoAnalysis(
        width=width,
        height=height,
        fps=round(src_fps, 3),
        duration_s=round(duration_s, 3),
        frames=frames,
        camera_motion=round(camera_motion, 5),
        representative_frame=representative,
    )
