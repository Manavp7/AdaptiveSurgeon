"""Live OR simulation over WebSocket.

Streams a procedure's phase/advisory/risk events in time order, scaled by a
playback speed, to demonstrate the real-time Copilot reacting phase-by-phase.
Reads persisted analysis (no heavy compute) and replays it on a virtual clock.
"""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ..db import SessionLocal
from ..models import Event, Procedure, RiskAssessment

router = APIRouter(tags=["live"])


def _build_timeline(db, procedure_id: str) -> tuple[list[dict], float]:
    proc = db.get(Procedure, procedure_id)
    if not proc:
        return [], 0.0
    video = next((m for m in proc.media if m.kind == "video"), None)
    duration = (video.duration_s if video else 0.0) or 0.0

    events: list[dict] = []
    for e in db.query(Event).filter(Event.procedure_id == procedure_id).all():
        if e.kind in ("phase", "advisory"):
            events.append({
                "t": e.t_start_s, "type": e.kind, "label": e.label,
                "severity": e.severity, "payload": e.payload,
            })
    for r in db.query(RiskAssessment).filter(RiskAssessment.procedure_id == procedure_id).all():
        if r.probability >= 0.5:
            events.append({
                "t": r.t_s, "type": "risk",
                "label": f"{r.event_type.replace('_', ' ')} ({int(r.probability * 100)}%)",
                "severity": r.severity, "payload": {"probability": r.probability},
            })
    events.sort(key=lambda x: x["t"])
    return events, duration


@router.websocket("/ws/procedures/{procedure_id}/live")
async def live_or(websocket: WebSocket, procedure_id: str, speed: float = 4.0):
    await websocket.accept()
    db = SessionLocal()
    try:
        events, duration = _build_timeline(db, procedure_id)
    finally:
        db.close()

    if duration <= 0:
        await websocket.send_json({"type": "error", "message": "No analyzed video to replay."})
        await websocket.close()
        return

    speed = max(0.5, min(20.0, speed))
    await websocket.send_json({
        "type": "meta", "duration": duration, "events": len(events), "speed": speed,
    })

    try:
        clock = 0.0
        for ev in events:
            gap = max(0.0, ev["t"] - clock)
            await asyncio.sleep(gap / speed)
            clock = ev["t"]
            await websocket.send_json({
                "type": "event",
                "category": ev["type"],  # phase | advisory | risk
                "clock": round(clock, 2),
                "t": ev["t"],
                "label": ev["label"],
                "severity": ev["severity"],
                "payload": ev["payload"],
            })
        # drain to end of procedure
        await asyncio.sleep(max(0.0, (duration - clock)) / speed)
        await websocket.send_json({"type": "done", "clock": round(duration, 2)})
        await websocket.close()
    except WebSocketDisconnect:
        return
    except Exception:  # noqa: BLE001
        try:
            await websocket.close()
        except Exception:  # noqa: BLE001
            pass
