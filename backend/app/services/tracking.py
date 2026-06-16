"""Instrument tracking + motion analytics (Subsystem 2).

A lightweight, deterministic multi-object tracker: detections are associated to
tracks per class using nearest-centroid matching across consecutive sampled
frames. From each track we compute the motion analytics the vision calls for:
path length, mean/max speed, idle time, and a tremor proxy (mean jerk).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from ..providers.base import DetectionResult


@dataclass
class _LiveTrack:
    track_id: int
    class_name: str
    points: list[list[float]] = field(default_factory=list)  # [t, cx, cy]
    last_t: float = 0.0


@dataclass
class TrackMetrics:
    track_id: int
    class_name: str
    path_length_m: float
    mean_speed_cm_s: float
    max_speed_cm_s: float
    idle_time_s: float
    active_time_s: float
    jerk: float
    speed_std_cm_s: float
    points: list[list[float]]


# centroid distance (normalized units) above which we start a new track
_MATCH_THRESHOLD = 0.18
_IDLE_SPEED_CM_S = 1.0  # below this instantaneous speed counts as idle


class CentroidTracker:
    def __init__(self, pixels_per_meter: float, frame_diag_px: float):
        self.ppm = pixels_per_meter
        self.frame_diag_px = frame_diag_px
        self._tracks: dict[str, list[_LiveTrack]] = {}
        self._next_id = 0

    def update(self, t_s: float, detections: list[DetectionResult]) -> None:
        by_class: dict[str, list[DetectionResult]] = {}
        for d in detections:
            by_class.setdefault(d.class_name, []).append(d)

        for cls, dets in by_class.items():
            live = self._tracks.setdefault(cls, [])
            for d in dets:
                cx, cy = d.x + d.w / 2.0, d.y + d.h / 2.0
                match = self._nearest(live, cx, cy)
                if match is None:
                    match = _LiveTrack(track_id=self._next_id, class_name=cls)
                    self._next_id += 1
                    live.append(match)
                match.points.append([round(t_s, 3), round(cx, 5), round(cy, 5)])
                match.last_t = t_s

    @staticmethod
    def _nearest(live: list[_LiveTrack], cx: float, cy: float) -> _LiveTrack | None:
        best, best_d = None, _MATCH_THRESHOLD
        for tr in live:
            if not tr.points:
                continue
            _, px, py = tr.points[-1]
            d = math.hypot(cx - px, cy - py)
            if d < best_d:
                best, best_d = tr, d
        return best

    def metrics(self) -> list[TrackMetrics]:
        out: list[TrackMetrics] = []
        # normalized distance -> pixels -> meters
        norm_to_m = self.frame_diag_px / (self.ppm * math.sqrt(2.0))
        for live in self._tracks.values():
            for tr in live:
                if len(tr.points) < 2:
                    continue
                out.append(self._track_metrics(tr, norm_to_m))
        out.sort(key=lambda m: (m.class_name, m.track_id))
        return out

    def _track_metrics(self, tr: _LiveTrack, norm_to_m: float) -> TrackMetrics:
        pts = tr.points
        path_m = 0.0
        speeds: list[float] = []  # cm/s
        idle = 0.0
        active = 0.0
        for i in range(1, len(pts)):
            t0, x0, y0 = pts[i - 1]
            t1, x1, y1 = pts[i]
            dt = max(t1 - t0, 1e-6)
            dist_norm = math.hypot(x1 - x0, y1 - y0)
            dist_m = dist_norm * norm_to_m
            path_m += dist_m
            speed_cm_s = (dist_m * 100.0) / dt
            speeds.append(speed_cm_s)
            if speed_cm_s < _IDLE_SPEED_CM_S:
                idle += dt
            else:
                active += dt

        # tremor proxy: mean absolute change in speed (jerk-like)
        jerk = 0.0
        if len(speeds) >= 2:
            jerk = sum(
                abs(speeds[i] - speeds[i - 1]) for i in range(1, len(speeds))
            ) / (len(speeds) - 1)

        mean_speed = sum(speeds) / len(speeds) if speeds else 0.0
        max_speed = max(speeds) if speeds else 0.0
        # speed variability (precision proxy): erratic motion has high std
        speed_std = 0.0
        if len(speeds) >= 2:
            var = sum((s - mean_speed) ** 2 for s in speeds) / len(speeds)
            speed_std = math.sqrt(var)
        return TrackMetrics(
            track_id=tr.track_id,
            class_name=tr.class_name,
            path_length_m=round(path_m, 4),
            mean_speed_cm_s=round(mean_speed, 3),
            max_speed_cm_s=round(max_speed, 3),
            idle_time_s=round(idle, 3),
            active_time_s=round(active, 3),
            jerk=round(jerk, 4),
            speed_std_cm_s=round(speed_std, 3),
            points=pts,
        )
