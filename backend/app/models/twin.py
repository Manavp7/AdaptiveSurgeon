"""Digital twin models (Subsystem 8).

Stores anatomy metadata derived from pre-op imaging and the expected-vs-actual
comparison surfaced during/after surgery. Geometry is referenced by URI in
object storage; metadata lives here for fast querying.
"""

from __future__ import annotations

from sqlalchemy import JSON, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base
from .base import IdMixin, TimestampMixin


class DigitalTwin(IdMixin, TimestampMixin, Base):
    __tablename__ = "digital_twins"

    procedure_id: Mapped[str] = mapped_column(
        ForeignKey("procedures.id", ondelete="CASCADE"), index=True, unique=True
    )
    source_modality: Mapped[str] = mapped_column(String(16), default="ct")
    # List of anatomy structures with criticality + simple geometry params:
    # {name, criticality(safe|caution|critical), color, geometry:{type,...}}
    structures: Mapped[list] = mapped_column(JSON, default=list)
    # Optional URI to a generated mesh/volume artifact in object storage.
    mesh_uri: Mapped[str | None] = mapped_column(String(512), nullable=True)
    # Differences detected between expected anatomy and intra-op observation.
    expected_vs_actual: Mapped[list] = mapped_column(JSON, default=list)
