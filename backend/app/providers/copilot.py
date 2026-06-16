"""CopilotProvider implementations (Subsystem 6) — ADVISORY ONLY.

Default: RuleCopilot — converts current surgical context (procedure type, phase
timeline, risk timeline) into time-anchored advisories. Never autonomous; every
message is guidance for the surgeon. An LLM-backed provider can replace this by
implementing ``advise(context)``.
"""

from __future__ import annotations

from .base import AdvisoryResult, CopilotProvider

# Phase-specific guidance (illustrative best-practice prompts).
_PHASE_ADVICE = {
    "access": ("Confirm safe port placement and pneumoperitoneum.", "info"),
    "exposure": ("Establish clear exposure of Calot's triangle.", "info"),
    "dissection": (
        "Possible bile duct nearby — dissect the hepatocystic triangle carefully.",
        "medium",
    ),
    "clipping": (
        "Confirm the Critical View of Safety before applying clips.",
        "high",
    ),
    "removal": ("Maintain traction; avoid gallbladder perforation.", "medium"),
    "closure": ("Inspect for bleeding/bile leak before closure.", "info"),
}


class RuleCopilot(CopilotProvider):
    name = "rules"

    def advise(self, context: dict) -> list[AdvisoryResult]:
        phases = context.get("phases", [])
        risks = context.get("risks", [])
        advisories: list[AdvisoryResult] = []

        # 1) Phase-driven guidance.
        for ph in phases:
            text, sev = _PHASE_ADVICE.get(ph["phase"], (None, "info"))
            if text:
                advisories.append(
                    AdvisoryResult(
                        t_start_s=ph["t_start_s"],
                        t_end_s=ph["t_end_s"],
                        label=text,
                        severity=sev,
                        payload={"phase": ph["phase"], "source": "phase_guidance"},
                    )
                )

        # 2) Risk-driven escalations (connect risk engine -> copilot).
        for r in risks:
            if r["probability"] >= 0.6:
                advisories.append(
                    AdvisoryResult(
                        t_start_s=r["t_s"],
                        label=(
                            f"Elevated {r['event_type'].replace('_', ' ')} risk "
                            f"({int(r['probability'] * 100)}%) — pause and reassess."
                        ),
                        severity="high",
                        payload={
                            "event_type": r["event_type"],
                            "probability": r["probability"],
                            "source": "risk_escalation",
                        },
                    )
                )

        advisories.sort(key=lambda a: a.t_start_s)
        return advisories
