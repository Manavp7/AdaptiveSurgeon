"""Surgical Skill Engine (Subsystem 5).

Turns objective motion analytics into interpretable subscores and an overall
0-100 skill score, plus human-readable findings. Designed to be monotonic:
smoother, more economical, more workflow-adherent motion scores higher.

Constants are calibrated against the synthetic seed so that the "expert" case
scores clearly higher than the "novice" case; they are not clinical thresholds.
"""

from __future__ import annotations

from dataclasses import dataclass

from .tracking import TrackMetrics


def _clamp(v: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, v))


# Subscore weights (sum to 1.0). Mirrors the vision's skill dimensions:
# Motion Efficiency, Precision, Tremor, Camera Stability, Tool Usage, Workflow.
_WEIGHTS = {
    "motion_economy": 0.22,
    "precision": 0.18,
    "tremor_control": 0.2,
    "camera_stability": 0.18,
    "tool_handling": 0.07,
    "workflow_adherence": 0.15,
}

# Calibration constants (tuned against the synthetic seed; not clinical
# thresholds). Each signal increases as skill drops, so every subscore ranks
# an expert above a novice -> the overall score is monotonic in skill.
_ECON_RATE = 0.007       # expected m of travel per second for clean technique
_ECON_K = 320.0          # penalty per excess metre of travel
_PRECISION_K = 60.0      # penalty per cm/s of speed variability
_TREMOR_K = 68.0         # penalty per unit jerk
_CAMERA_K = 4200.0       # penalty per unit camera motion
_TOOL_K = 45.0           # penalty per cm/s of mean instrument speed


@dataclass
class SkillResult:
    score: float
    subscores: dict
    findings: list


def compute_skill(
    track_metrics: list[TrackMetrics],
    phases: list[dict],
    duration_s: float,
    camera_motion: float = 0.0,
) -> SkillResult:
    if not track_metrics:
        return SkillResult(score=0.0, subscores={}, findings=["No instrument motion detected."])

    n = len(track_metrics)
    total_path = sum(m.path_length_m for m in track_metrics)
    mean_jerk = sum(m.jerk for m in track_metrics) / n
    mean_speed = sum(m.mean_speed_cm_s for m in track_metrics) / n
    mean_speed_std = sum(m.speed_std_cm_s for m in track_metrics) / n
    total_idle = sum(m.idle_time_s for m in track_metrics)
    total_active = sum(m.active_time_s for m in track_metrics)
    idle_ratio = total_idle / (total_idle + total_active) if (total_idle + total_active) else 0.0
    mean_phase_conf = (
        sum(p["confidence"] for p in phases) / len(phases) if phases else 0.5
    )

    expected_path = _ECON_RATE * max(duration_s, 1.0)

    # --- subscores: all monotonic-decreasing in "badness" signals ---
    motion_economy = _clamp(100.0 - _ECON_K * max(0.0, total_path - expected_path))
    precision = _clamp(100.0 - _PRECISION_K * mean_speed_std)
    tremor_control = _clamp(100.0 - _TREMOR_K * mean_jerk)
    camera_stability = _clamp(100.0 - _CAMERA_K * camera_motion)
    tool_handling = _clamp(100.0 - _TOOL_K * max(0.0, mean_speed - 0.3))
    workflow_adherence = _clamp(100.0 * mean_phase_conf)

    subscores = {
        "motion_economy": round(motion_economy, 1),
        "precision": round(precision, 1),
        "tremor_control": round(tremor_control, 1),
        "camera_stability": round(camera_stability, 1),
        "tool_handling": round(tool_handling, 1),
        "workflow_adherence": round(workflow_adherence, 1),
    }
    score = round(sum(subscores[k] * w for k, w in _WEIGHTS.items()), 1)

    findings = _findings(
        subscores, total_path, idle_ratio, mean_jerk, mean_speed, mean_speed_std
    )
    return SkillResult(score=score, subscores=subscores, findings=findings)


def _findings(
    subscores: dict,
    total_path: float,
    idle_ratio: float,
    mean_jerk: float,
    mean_speed: float,
    mean_speed_std: float,
) -> list:
    out: list = []
    if subscores["motion_economy"] < 75:
        out.append(
            f"High instrument travel ({total_path:.2f} m) — improve motion economy."
        )
    if subscores["precision"] < 75:
        out.append(
            f"Erratic instrument speed (variability {mean_speed_std:.2f} cm/s) — work on precision."
        )
    if subscores["tremor_control"] < 75:
        out.append(f"Elevated tremor proxy (jerk {mean_jerk:.2f}).")
    if subscores["camera_stability"] < 75:
        out.append("Excessive camera movement — stabilize the laparoscope view.")
    if subscores["tool_handling"] < 75:
        out.append(f"High mean instrument speed ({mean_speed:.2f} cm/s).")
    if subscores["workflow_adherence"] < 75:
        out.append("Workflow adherence below expected for this procedure.")
    if not out:
        out.append("Strong, controlled technique across all measured dimensions.")
    return out
