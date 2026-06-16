"""Train a phase classifier (M4 demonstration).

Generates window-level samples from the canonical phase structure (time position
+ which instruments are present) and fits a small classifier mapping those
features to the surgical phase. The model provider uses it to label windows and
assemble a phase timeline. Fully offline; synthetic labels.
"""

from __future__ import annotations

import numpy as np

from . import PHASE_MODEL_PATH
from .features import phase_features


def build_dataset(samples: int = 6000, seed: int = 1):
    from ..constants import PHASE_INSTRUMENTS, PHASES

    # canonical relative phase durations -> probability of sampling each phase
    weights = {"access": 0.08, "exposure": 0.15, "dissection": 0.34,
               "clipping": 0.13, "removal": 0.20, "closure": 0.10}
    # cumulative time boundaries to derive a realistic time_fraction per phase
    bounds, cursor = {}, 0.0
    for ph in PHASES:
        bounds[ph] = (cursor, cursor + weights[ph])
        cursor += weights[ph]

    rng = np.random.RandomState(seed)
    X, y = [], []
    phase_list = list(PHASES)
    probs = np.array([weights[p] for p in phase_list])
    probs = probs / probs.sum()
    for _ in range(samples):
        ph = rng.choice(phase_list, p=probs)
        lo, hi = bounds[ph]
        tf = rng.uniform(lo, hi)
        expected = PHASE_INSTRUMENTS.get(ph, [])
        present = [c for c in expected if rng.uniform() < 0.85]
        # occasional spurious instrument (noise)
        if rng.uniform() < 0.1:
            present.append(rng.choice(list({i for v in PHASE_INSTRUMENTS.values() for i in v})))
        X.append(phase_features(tf, present))
        y.append(ph)
    return np.array(X), np.array(y)


def train(seed: int = 1) -> dict:
    from sklearn.ensemble import RandomForestClassifier
    import joblib

    X, y = build_dataset(seed=seed)
    model = RandomForestClassifier(n_estimators=60, max_depth=8, random_state=seed)
    model.fit(X, y)
    acc = float(model.score(X, y))
    PHASE_MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({"model": model, "kind": "phase_rf"}, PHASE_MODEL_PATH)
    return {"path": str(PHASE_MODEL_PATH), "samples": len(y), "train_accuracy": round(acc, 4)}


if __name__ == "__main__":  # pragma: no cover
    print(train())
