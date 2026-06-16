"""Foundation / Case-search endpoints (Subsystem 9)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Procedure
from ..providers import get_embedding_provider
from ..schemas.foundation import (
    AskRequest,
    AskResponse,
    SimilarCase,
    SimilarCasesResponse,
)
from ..services import foundation

router = APIRouter(prefix="/foundation", tags=["foundation"])


@router.get("/similar", response_model=SimilarCasesResponse)
def similar(
    db: Annotated[Session, Depends(get_db)],
    procedure_id: str = Query(...),
    top_k: int = Query(5, ge=1, le=20),
) -> SimilarCasesResponse:
    if not db.get(Procedure, procedure_id):
        raise HTTPException(status_code=404, detail="Procedure not found")
    results = foundation.similar_cases(db, procedure_id, top_k)
    return SimilarCasesResponse(
        query_procedure_id=procedure_id,
        provider=get_embedding_provider().name,
        results=[SimilarCase(**r) for r in results],
    )


@router.get("/search", response_model=SimilarCasesResponse)
def search(
    db: Annotated[Session, Depends(get_db)],
    q: str = Query(..., min_length=1),
    top_k: int = Query(5, ge=1, le=20),
) -> SimilarCasesResponse:
    results = foundation.search_by_text(db, q, top_k)
    return SimilarCasesResponse(
        query_procedure_id="", provider=get_embedding_provider().name,
        results=[SimilarCase(**r) for r in results],
    )


@router.post("/ask", response_model=AskResponse)
def ask(payload: AskRequest, db: Annotated[Session, Depends(get_db)]) -> AskResponse:
    result = foundation.answer_question(
        db, payload.question, payload.procedure_id, payload.top_k
    )
    return AskResponse(
        question=result["question"], answer=result["answer"],
        provider=result["provider"],
        cited_cases=[SimilarCase(**c) for c in result["cited_cases"]],
    )
