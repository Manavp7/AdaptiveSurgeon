"""Train a logistic-regression risk model (M4 demonstration).

Generates a synthetic dataset from the rule-based risk priors (sampling binary
outcomes ~ Bernoulli(rule_probability)) and fits a LogisticRegression that
learns a smooth probability function over the engineered features. This shows
the trained-model pathway end-to-end, fully offline. Labels are synthetic and
carry no clinical meaning.
"""

from __future__ import annotations

import numpy as np

from . import RISK_MODEL_PATH
from .features import risk_features


def build_dataset(n_per_combo: int = 400, seed: int = 0):
    from ..providers.risk import _PHASE_RISK

    rng = np.random.RandomState(seed)
    X, y = [], []
    for phase, events in _PHASE_RISK.items():
        for event, baseline in events.items():
            for _ in range(n_per_combo):
                motion = rng.uniform(0, 1)
                tremor = rng.uniform(0, 1)
                logit = -1.4 + 4.0 * baseline + 1.6 * motion + 1.2 * tremor
                prob = 1.0 / (1.0 + np.exp(-logit))
                label = 1 if rng.uniform() < prob else 0
                X.append(risk_features(phase, event, baseline, motion, tremor))
                y.append(label)
    return np.array(X), np.array(y)


def train(seed: int = 0) -> dict:
    from sklearn.linear_model import LogisticRegression
    import joblib

    X, y = build_dataset(seed=seed)
    model = LogisticRegression(max_iter=1000)
    model.fit(X, y)
    acc = float(model.score(X, y))
    RISK_MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({"model": model, "kind": "risk_logreg"}, RISK_MODEL_PATH)
    return {"path": str(RISK_MODEL_PATH), "samples": len(y), "train_accuracy": round(acc, 4)}


if __name__ == "__main__":  # pragma: no cover
    print(train())
