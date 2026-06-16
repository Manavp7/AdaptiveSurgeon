"""Cross-procedure analytics (surgeon scorecards / leaderboard)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Procedure, SkillReport

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/surgeons")
def surgeon_scorecards(db: Annotated[Session, Depends(get_db)]) -> dict:
    """Aggregate skill + complication metrics per surgeon."""
    procs = db.query(Procedure).all()
    skills = {s.procedure_id: s.score for s in db.query(SkillReport).all()}

    agg: dict[str, dict] = {}
    for p in procs:
        key = p.surgeon_name or p.surgeon_id or "Unknown"
        a = agg.setdefault(key, {
            "surgeon": key, "cases": 0, "analyzed": 0,
            "skill_sum": 0.0, "skill_scores": [],
            "complications": 0, "procedure_types": set(),
        })
        a["cases"] += 1
        a["procedure_types"].add(p.procedure_type)
        if p.id in skills:
            a["analyzed"] += 1
            a["skill_sum"] += skills[p.id]
            a["skill_scores"].append({"procedure_id": p.id, "score": skills[p.id],
                                      "created_at": p.created_at.isoformat() if p.created_at else None})
        if p.outcome and p.outcome.complications:
            a["complications"] += len(p.outcome.complications)

    out = []
    for a in agg.values():
        analyzed = a["analyzed"]
        out.append({
            "surgeon": a["surgeon"],
            "cases": a["cases"],
            "analyzed": analyzed,
            "avg_skill": round(a["skill_sum"] / analyzed, 1) if analyzed else None,
            "complication_rate": round(a["complications"] / a["cases"], 2) if a["cases"] else 0.0,
            "procedure_types": sorted(a["procedure_types"]),
            "trend": sorted(a["skill_scores"], key=lambda s: s["created_at"] or ""),
        })
    out.sort(key=lambda x: (x["avg_skill"] is not None, x["avg_skill"] or 0), reverse=True)
    return {"surgeons": out}
