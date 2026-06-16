"""InstrumentDetectionProvider implementations.

Default: SyntheticDetector — deterministic HSV color segmentation that detects
the instruments rendered by the synthetic video generator. Fully offline.

Optional: YoloDetector — uses ultralytics if installed and enabled. Guarded so
the platform never breaks offline; falls back to synthetic if unavailable.
"""

from __future__ import annotations

import cv2
import numpy as np

from ..constants import INSTRUMENTS
from .base import DetectionResult, InstrumentDetectionProvider

MIN_AREA_FRAC = 0.0008  # ignore specks smaller than this fraction of the frame


class SyntheticDetector(InstrumentDetectionProvider):
    """Color-based deterministic detector matched to the synthetic generator."""

    name = "synthetic"

    def detect(self, frame: np.ndarray, t_s: float) -> list[DetectionResult]:
        h, w = frame.shape[:2]
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        min_area = MIN_AREA_FRAC * h * w
        results: list[DetectionResult] = []

        for cls, spec in INSTRUMENTS.items():
            lo = np.array(spec["hsv_lo"], dtype=np.uint8)
            hi = np.array(spec["hsv_hi"], dtype=np.uint8)
            mask = cv2.inRange(hsv, lo, hi)
            mask = cv2.morphologyEx(
                mask, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8)
            )
            contours, _ = cv2.findContours(
                mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
            )
            if not contours:
                continue
            # Largest blob of this color = the instrument shaft/tip.
            cnt = max(contours, key=cv2.contourArea)
            area = cv2.contourArea(cnt)
            if area < min_area:
                continue
            bx, by, bw, bh = cv2.boundingRect(cnt)
            conf = float(min(1.0, 0.5 + area / (h * w) * 6.0))
            results.append(
                DetectionResult(
                    class_name=cls,
                    confidence=round(conf, 3),
                    x=round(bx / w, 5),
                    y=round(by / h, 5),
                    w=round(bw / w, 5),
                    h=round(bh / h, 5),
                )
            )
        return results


class YoloDetector(InstrumentDetectionProvider):
    """Optional ultralytics YOLO detector (drop-in real model)."""

    name = "yolo"

    def __init__(self, weights: str = "yolov8n.pt"):
        from ultralytics import YOLO  # noqa: F401  (raises if not installed)

        self._model = YOLO(weights)

    def detect(self, frame: np.ndarray, t_s: float) -> list[DetectionResult]:
        h, w = frame.shape[:2]
        out: list[DetectionResult] = []
        res = self._model.predict(frame, verbose=False)[0]
        for box in res.boxes:
            x1, y1, x2, y2 = box.xyxy[0].tolist()
            cls_id = int(box.cls[0])
            name = res.names.get(cls_id, str(cls_id))
            out.append(
                DetectionResult(
                    class_name=name,
                    confidence=float(box.conf[0]),
                    x=x1 / w,
                    y=y1 / h,
                    w=(x2 - x1) / w,
                    h=(y2 - y1) / h,
                )
            )
        return out
