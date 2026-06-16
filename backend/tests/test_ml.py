"""Tests for the trainable M4 models + graceful fallback."""

from __future__ import annotations

from app.ml import train_phase, train_risk
from app.providers.phase import HeuristicPhases, ModelPhases
from app.providers.risk import ModelRisk, RuleRisk


def test_train_and_use_risk_model():
    info = train_risk.train(seed=0)
    assert info["samples"] > 0
    provider = ModelRisk()  # loads the joblib model
    phases = [{"phase": "dissection", "t_start_s": 0, "t_end_s": 10}]
    out = provider.assess({"phases": phases, "motion_intensity": 0.8, "tremor": 0.7})
    assert out
    assert all(0.0 <= r.probability <= 1.0 for r in out)


def test_train_and_use_phase_model():
    train_phase.train(seed=1)
    provider = ModelPhases()
    timeline = [
        {"t_s": float(t), "classes": (["grasper", "hook"] if t < 60 else ["clip_applier", "grasper"])}
        for t in range(0, 100, 5)
    ]
    phases = provider.phases("lap_chole", 100.0, [], timeline)
    assert phases
    # ordered and within bounds
    assert phases[0].t_start_s == 0
    assert abs(phases[-1].t_end_s - 100.0) < 1e-6


def test_providers_have_rule_fallbacks():
    # rule/heuristic providers always work without any model file
    assert RuleRisk().assess({"phases": [{"phase": "clipping", "t_start_s": 0, "t_end_s": 5}],
                              "motion_intensity": 0.5, "tremor": 0.5})
    assert HeuristicPhases().phases("lap_chole", 10.0, [], [{"t_s": 1.0, "classes": ["grasper"]}])
