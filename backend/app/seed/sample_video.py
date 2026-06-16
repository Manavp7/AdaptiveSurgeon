"""Deterministic synthetic laparoscopic video generator.

Renders a reddish "tissue" background with colored instruments that enter from
the frame edges and move through the canonical procedure phases. The ``skill``
parameter (0..1) controls motion smoothness, path length, idle time and camera
shake so the downstream Skill Engine produces clearly different scores for
"expert" vs "novice" cases.

Frames are piped to the system ffmpeg (libx264) to produce a browser-playable
H.264 MP4. If ffmpeg is unavailable we fall back to OpenCV's mp4v writer (still
analyzable, but may not stream in all browsers).
"""

from __future__ import annotations

import logging
import shutil
import subprocess
from pathlib import Path

import cv2
import numpy as np

from ..constants import INSTRUMENTS, PHASE_INSTRUMENTS, PHASES

log = logging.getLogger("adaptivesurgeon.seed.video")

# Phase relative durations (match the heuristic phase provider).
_PHASE_WEIGHTS = {
    "access": 0.08, "exposure": 0.15, "dissection": 0.34,
    "clipping": 0.13, "removal": 0.20, "closure": 0.10,
}

# Instrument entry points (normalized) at frame borders.
_ENTRY = {
    "grasper": (0.02, 0.98),
    "hook": (0.98, 0.98),
    "scissors": (0.98, 0.02),
    "clip_applier": (0.02, 0.02),
    "needle_holder": (0.5, 0.99),
}
# Per-instrument working target region (normalized).
_TARGET = {
    "grasper": (0.45, 0.5),
    "hook": (0.6, 0.45),
    "scissors": (0.55, 0.4),
    "clip_applier": (0.5, 0.55),
    "needle_holder": (0.5, 0.5),
}


def _phase_boundaries(duration_s: float) -> list[tuple[str, float, float]]:
    out, cursor = [], 0.0
    for i, ph in enumerate(PHASES):
        seg = _PHASE_WEIGHTS[ph] * duration_s
        t0 = cursor
        t1 = duration_s if i == len(PHASES) - 1 else cursor + seg
        cursor = t1
        out.append((ph, t0, t1))
    return out


def _make_background(rng: np.random.RandomState, h: int, w: int) -> np.ndarray:
    """Reddish tissue background with smooth low-frequency variation + vignette."""
    low = rng.randint(0, 60, size=(h // 16 + 1, w // 16 + 1, 3)).astype(np.float32)
    low = cv2.resize(low, (w, h), interpolation=cv2.INTER_CUBIC)
    base = np.zeros((h, w, 3), np.float32)
    base[..., 0] = 40 + low[..., 0] * 0.4   # B
    base[..., 1] = 55 + low[..., 1] * 0.5   # G
    base[..., 2] = 150 + low[..., 2] * 0.6  # R (tissue)
    # vignette
    yy, xx = np.mgrid[0:h, 0:w]
    cy, cx = h / 2, w / 2
    r = np.sqrt(((xx - cx) / cx) ** 2 + ((yy - cy) / cy) ** 2)
    vig = np.clip(1.15 - 0.5 * r, 0.45, 1.0).astype(np.float32)
    base *= vig[..., None]
    return np.clip(base, 0, 255).astype(np.uint8)


def _draw_instrument(img, entry, tip, color, thickness):
    h, w = img.shape[:2]
    p0 = (int(entry[0] * w), int(entry[1] * h))
    p1 = (int(tip[0] * w), int(tip[1] * h))
    cv2.line(img, p0, p1, color, thickness, lineType=cv2.LINE_AA)
    cv2.circle(img, p1, max(thickness, 5), color, -1, lineType=cv2.LINE_AA)


def render_surgical_video(
    out_path: str | Path,
    seed: int,
    skill: float = 0.7,
    duration_s: float = 20.0,
    fps: int = 12,
    size: tuple[int, int] = (640, 360),
) -> dict:
    w, h = size
    rng = np.random.RandomState(seed)
    n_frames = int(duration_s * fps)
    bounds = _phase_boundaries(duration_s)
    background = _make_background(rng, h, w)

    jitter = (1.0 - skill) * 0.06          # tip noise amplitude (normalized)
    shake = (1.0 - skill) * 6.0            # camera shake (pixels)
    drift = (1.0 - skill) * 0.12           # extra wandering of the tip path

    # Precompute smooth per-instrument phase offsets for deterministic motion.
    inst_phase = {k: rng.uniform(0, 2 * np.pi) for k in INSTRUMENTS}

    writer = _Writer(out_path, fps, size)
    try:
        for fi in range(n_frames):
            t = fi / fps
            frame = background.copy()

            # current phase
            phase = next((p for p, a, b in bounds if a <= t < b), PHASES[-1])
            active = PHASE_INSTRUMENTS.get(phase, [])

            for inst in active:
                entry = _ENTRY[inst]
                tx, ty = _TARGET[inst]
                ph = inst_phase[inst]
                # smooth circular working motion + wandering + jitter
                tip_x = tx + 0.08 * np.cos(1.5 * t + ph) + drift * np.sin(0.6 * t + ph)
                tip_y = ty + 0.08 * np.sin(1.5 * t + ph) + drift * np.cos(0.5 * t + ph)
                tip_x += rng.uniform(-jitter, jitter)
                tip_y += rng.uniform(-jitter, jitter)
                tip = (np.clip(tip_x, 0.05, 0.95), np.clip(tip_y, 0.05, 0.95))
                _draw_instrument(frame, entry, tip, INSTRUMENTS[inst]["bgr"], thickness=9)

            # camera shake (global translation)
            if shake > 0.5:
                dx = int(rng.uniform(-shake, shake))
                dy = int(rng.uniform(-shake, shake))
                M = np.float32([[1, 0, dx], [0, 1, dy]])
                frame = cv2.warpAffine(frame, M, (w, h), borderMode=cv2.BORDER_REFLECT)

            writer.write(frame)
    finally:
        writer.release()

    return {
        "path": str(out_path),
        "fps": fps,
        "duration_s": round(n_frames / fps, 3),
        "width": w,
        "height": h,
        "frames": n_frames,
        "codec": writer.codec,
    }


class _Writer:
    """H.264 via ffmpeg pipe; OpenCV mp4v fallback."""

    def __init__(self, out_path: str | Path, fps: int, size: tuple[int, int]):
        self.out_path = str(out_path)
        self.fps = fps
        self.size = size
        self.codec = "h264"
        self._proc = None
        self._cv = None
        Path(self.out_path).parent.mkdir(parents=True, exist_ok=True)

        if shutil.which("ffmpeg"):
            w, h = size
            cmd = [
                "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                "-f", "rawvideo", "-pix_fmt", "bgr24",
                "-s", f"{w}x{h}", "-r", str(fps), "-i", "-",
                "-c:v", "libx264", "-pix_fmt", "yuv420p",
                "-movflags", "+faststart", self.out_path,
            ]
            try:
                self._proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
            except Exception as exc:  # pragma: no cover
                log.warning("ffmpeg pipe failed (%s); using OpenCV fallback.", exc)
                self._proc = None

        if self._proc is None:
            self.codec = "mp4v"
            self._cv = cv2.VideoWriter(
                self.out_path, cv2.VideoWriter_fourcc(*"mp4v"), fps, size
            )

    def write(self, frame: np.ndarray) -> None:
        if self._proc is not None:
            self._proc.stdin.write(frame.tobytes())
        else:
            self._cv.write(frame)

    def release(self) -> None:
        if self._proc is not None:
            self._proc.stdin.close()
            self._proc.wait()
        if self._cv is not None:
            self._cv.release()
