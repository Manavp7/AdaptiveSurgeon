"""Trainable ML models (M4).

Lightweight scikit-learn models that demonstrate the real ML pathway for the
risk and phase providers. Models are trained offline from synthetic features and
saved to ``backend/data/models/*.joblib``; the corresponding providers load them
when ``ADAPTIVE_RISK_PROVIDER=model`` / ``ADAPTIVE_PHASE_PROVIDER=model`` and
fall back to the rule/heuristic providers if the model file or scikit-learn is
unavailable. This keeps the default path fully offline.
"""

from pathlib import Path

from ..config import BACKEND_DIR

MODELS_DIR = BACKEND_DIR / "data" / "models"
RISK_MODEL_PATH = MODELS_DIR / "risk_model.joblib"
PHASE_MODEL_PATH = MODELS_DIR / "phase_model.joblib"
