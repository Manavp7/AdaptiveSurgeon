"""Foundation / Case-Search service (Subsystem 9).

Builds a text summary per case, embeds it via the configured EmbeddingProvider,
and supports cosine similarity search + a retrieval-grounded Q&A scaffold. With
the default hashing embedder this is fully offline; a SentenceTransformer or LLM
provider drops in without interface changes. This is the seed of the
"GPT-for-surgery" knowledge layer described in the vision.
"""

from __future__ import annotations

import math

from sqlalchemy.orm import Session

from .. import models
from ..providers import get_embedding_provider


def build_case_summary(proc: "models.Procedure") -> str:
    parts = [f"Procedure: {proc.procedure_type}."]
    if proc.surgeon_name:
        parts.append(f"Surgeon: {proc.surgeon_name}.")
    patient = proc.patient
    if patient:
        demo = []
        if patient.age is not None:
            demo.append(f"{patient.age}y")
        if patient.sex:
            demo.append(patient.sex)
        if demo:
            parts.append("Patient: " + ", ".join(demo) + ".")
        if patient.history:
            parts.append("History: " + ", ".join(f"{k}={v}" for k, v in patient.history.items()) + ".")
    phases = sorted(proc.__dict__.get("_phase_labels", []) or [])
    if phases:
        parts.append("Phases: " + ", ".join(phases) + ".")
    if proc.outcome:
        comps = proc.outcome.complications or []
        if comps:
            parts.append("Complications: " + ", ".join(str(c) for c in comps) + ".")
        else:
            parts.append("Complications: none.")
        if proc.outcome.discharge_summary:
            parts.append(proc.outcome.discharge_summary)
    return " ".join(parts)


def cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def upsert_case_embedding(db: Session, proc: "models.Procedure") -> models.CaseEmbedding:
    provider = get_embedding_provider()
    summary = build_case_summary(proc)
    vector = provider.embed(summary)
    row = (
        db.query(models.CaseEmbedding)
        .filter(models.CaseEmbedding.procedure_id == proc.id)
        .one_or_none()
    )
    if row is None:
        row = models.CaseEmbedding(procedure_id=proc.id)
        db.add(row)
    row.provider = provider.name
    row.dim = provider.dim
    row.vector = vector
    row.text_summary = summary
    return row


def similar_cases(db: Session, procedure_id: str, top_k: int = 5) -> list[dict]:
    target = (
        db.query(models.CaseEmbedding)
        .filter(models.CaseEmbedding.procedure_id == procedure_id)
        .one_or_none()
    )
    if target is None:
        return []
    rows = db.query(models.CaseEmbedding).all()
    scored = []
    for r in rows:
        if r.procedure_id == procedure_id:
            continue
        scored.append((cosine(target.vector, r.vector), r))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [_case_dict(db, r, sim) for sim, r in scored[:top_k]]


def search_by_text(db: Session, query: str, top_k: int = 5) -> list[dict]:
    provider = get_embedding_provider()
    qvec = provider.embed(query)
    rows = db.query(models.CaseEmbedding).all()
    scored = [(cosine(qvec, r.vector), r) for r in rows]
    scored.sort(key=lambda x: x[0], reverse=True)
    return [_case_dict(db, r, sim) for sim, r in scored[:top_k]]


def _case_dict(db: Session, emb: models.CaseEmbedding, sim: float) -> dict:
    proc = db.get(models.Procedure, emb.procedure_id)
    complications = []
    outcome_summary = ""
    if proc and proc.outcome:
        complications = proc.outcome.complications or []
        outcome_summary = proc.outcome.discharge_summary or ""
    return {
        "procedure_id": emb.procedure_id,
        "procedure_type": proc.procedure_type if proc else "",
        "similarity": round(float(sim), 4),
        "text_summary": emb.text_summary,
        "complications": complications,
        "outcome_summary": outcome_summary,
    }


def answer_question(db: Session, question: str, procedure_id: str | None, top_k: int) -> dict:
    """Retrieval-grounded extractive answer (LLM-pluggable later)."""
    if procedure_id:
        cases = similar_cases(db, procedure_id, top_k)
    else:
        cases = search_by_text(db, question, top_k)

    provider = get_embedding_provider()
    if not cases:
        answer = "No comparable cases are available in the knowledge base yet."
    else:
        n = len(cases)
        comp_cases = [c for c in cases if c["complications"]]
        types = sorted({c["procedure_type"] for c in cases})
        answer = (
            f"Based on {n} similar case(s) ({', '.join(types)}), "
            f"{len(comp_cases)} had recorded complications"
        )
        if comp_cases:
            all_comps = sorted({str(x) for c in comp_cases for x in c["complications"]})
            answer += ": " + ", ".join(all_comps) + "."
        else:
            answer += " (none recorded)."
        answer += (
            " This grounded summary is advisory only and not a clinical recommendation."
        )
    return {
        "question": question,
        "answer": answer,
        "provider": provider.name,
        "cited_cases": cases,
    }
