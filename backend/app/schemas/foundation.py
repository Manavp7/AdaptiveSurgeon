"""Foundation / case-search schemas (Subsystem 9)."""

from __future__ import annotations

from pydantic import BaseModel


class SimilarCase(BaseModel):
    procedure_id: str
    procedure_type: str
    similarity: float
    text_summary: str
    complications: list = []
    outcome_summary: str = ""


class SimilarCasesResponse(BaseModel):
    query_procedure_id: str
    provider: str
    results: list[SimilarCase]


class AskRequest(BaseModel):
    question: str
    procedure_id: str | None = None
    top_k: int = 5


class AskResponse(BaseModel):
    question: str
    answer: str
    provider: str
    cited_cases: list[SimilarCase]
