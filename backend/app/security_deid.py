"""PHI de-identification helpers.

Pseudonymizes identifiers (e.g. MRN) with a keyed hash so the same input maps to
a stable token without storing the raw value when de-id is enabled. This is a
demonstration of the de-id pathway, not a certified de-identification process.
"""

from __future__ import annotations

import hashlib
import hmac

from .config import get_settings


def pseudonymize(value: str) -> str:
    """Return a stable, non-reversible token for an identifier."""
    settings = get_settings()
    digest = hmac.new(
        settings.auth_secret.encode(), (value or "").encode(), hashlib.sha256
    ).digest()
    return "anon_" + digest[:8].hex()
