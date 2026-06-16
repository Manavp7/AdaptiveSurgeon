"""Digital twin schemas (Subsystem 8)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class DigitalTwinOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    procedure_id: str
    source_modality: str
    structures: list
    mesh_uri: str | None
    expected_vs_actual: list
