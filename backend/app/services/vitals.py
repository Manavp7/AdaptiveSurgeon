"""Synthetic intra-op vitals generator.

Produces a deterministic ECG-derived vital-sign time series (heart rate, blood
pressure, SpO2) for a procedure. Baselines drift with mild noise, and
**high-risk moments perturb the signals** (tachycardia, hypotension, desat) so
the vitals visibly correlate with the risk timeline — reinforcing the connected
workflow. Real deployments would ingest actual monitor data via Media(kind=ecg);
this synthetic path keeps the offline demo coherent.
"""

from __future__ import annotations

import hashlib
import math


def _seed_float(seed: str) -> float:
    return int.from_bytes(hashlib.sha256(seed.encode()).digest()[:4], "big") / 0xFFFFFFFF


def generate_vitals(
    procedure_id: str,
    duration_s: float,
    risk_results: list[dict],
    step_s: float = 1.0,
) -> list[dict]:
    if duration_s <= 0:
        duration_s = 1.0
    base = _seed_float(procedure_id)
    hr0 = 68 + base * 14            # 68-82 bpm baseline
    bp_sys0 = 116 + base * 16       # 116-132
    bp_dia0 = 74 + base * 10        # 74-84
    spo20 = 97 + base * 2           # 97-99

    # High-risk events (prob >= 0.6) create transient perturbations.
    spikes = [(r["t_s"], r["probability"]) for r in risk_results if r["probability"] >= 0.6]

    series: list[dict] = []
    n = int(duration_s / step_s) + 1
    for i in range(n):
        t = round(i * step_s, 2)
        wobble = math.sin(t * 0.5 + base * 6) * 2.0
        # nearest high-risk influence (gaussian bump)
        influence = 0.0
        for st, p in spikes:
            influence = max(influence, p * math.exp(-((t - st) ** 2) / (2 * 4.0**2)))
        hr = hr0 + wobble + influence * 35.0
        bp_sys = bp_sys0 + wobble - influence * 22.0
        bp_dia = bp_dia0 + wobble * 0.6 - influence * 12.0
        spo2 = spo20 - influence * 4.0
        series.append({
            "t": t,
            "hr": round(hr, 1),
            "bp_sys": round(bp_sys, 1),
            "bp_dia": round(bp_dia, 1),
            "spo2": round(max(85.0, min(100.0, spo2)), 1),
        })
    return series
