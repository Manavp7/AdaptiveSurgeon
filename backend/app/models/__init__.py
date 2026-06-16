"""ORM models. Importing this package registers all tables on Base.metadata."""

from .analysis import (
    CaseEmbedding,
    Detection,
    PhaseSegment,
    RiskAssessment,
    SkillReport,
    Track,
)
from .audit import AuditLog
from .clinical import Event, Media, Outcome, Patient, Procedure
from .twin import DigitalTwin
from .user import User

__all__ = [
    "AuditLog",
    "Patient",
    "Procedure",
    "Media",
    "Event",
    "Outcome",
    "Detection",
    "Track",
    "PhaseSegment",
    "SkillReport",
    "RiskAssessment",
    "CaseEmbedding",
    "DigitalTwin",
    "User",
]
