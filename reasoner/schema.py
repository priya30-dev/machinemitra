"""The repair ticket every reasoner must produce, plus validation so a messy
LLM answer can never crash the app."""
from dataclasses import asdict, dataclass, field

URGENCY_LEVELS = ["critical", "high", "medium", "low"]
SKILLS = ["mechanical", "electrical", "hydraulic", "cnc", "plc_electronics", "welding", "pneumatic"]


@dataclass
class Cause:
    cause: str
    confidence: str = "medium"  # high | medium | low


@dataclass
class Ticket:
    machine_type: str = "unknown"
    machine_details: str = ""
    symptoms: list[str] = field(default_factory=list)
    probable_causes: list[Cause] = field(default_factory=list)
    urgency: str = "medium"
    urgency_reason: str = ""
    safety_risk: bool = False
    safety_reason: str = ""
    skills_required: list[str] = field(default_factory=list)
    parts_to_carry: list[str] = field(default_factory=list)
    tools_to_carry: list[str] = field(default_factory=list)
    follow_up_questions: list[str] = field(default_factory=list)
    safe_checks: list[str] = field(default_factory=list)  # first-aid while you wait
    caller_frustrated: bool = False
    owner_reply: str = ""          # spoken back to the owner, in their language
    technician_brief: str = ""     # short English brief for the technician
    caller_language: str = "hi-en"
    reasoner: str = "unknown"      # "evon" or "fallback" — shown in the UI for honesty

    def to_dict(self) -> dict:
        return asdict(self)


def _str_list(value, limit: int = 6) -> list[str]:
    if isinstance(value, str):
        value = [value]
    if not isinstance(value, list):
        return []
    return [str(v).strip() for v in value if str(v).strip()][:limit]


def from_dict(d: dict, reasoner: str) -> Ticket:
    """Coerce any dict (usually LLM output) into a valid Ticket."""
    d = d or {}
    causes = []
    for c in d.get("probable_causes") or []:
        if isinstance(c, dict) and c.get("cause"):
            conf = str(c.get("confidence", "medium")).lower()
            causes.append(Cause(str(c["cause"]), conf if conf in ("high", "medium", "low") else "medium"))
        elif isinstance(c, str) and c.strip():
            causes.append(Cause(c.strip()))
    urgency = str(d.get("urgency", "medium")).lower().strip()
    skills = [s.lower().replace(" ", "_").replace("/", "_") for s in _str_list(d.get("skills_required"))]
    skills = [s for s in skills if s in SKILLS] or ["mechanical"]
    return Ticket(
        machine_type=str(d.get("machine_type") or "unknown").strip(),
        machine_details=str(d.get("machine_details") or "").strip(),
        symptoms=_str_list(d.get("symptoms")),
        probable_causes=causes[:4],
        urgency=urgency if urgency in URGENCY_LEVELS else "medium",
        urgency_reason=str(d.get("urgency_reason") or "").strip(),
        safety_risk=bool(d.get("safety_risk", False)),
        safety_reason=str(d.get("safety_reason") or "").strip(),
        skills_required=skills,
        parts_to_carry=_str_list(d.get("parts_to_carry"), 8),
        tools_to_carry=_str_list(d.get("tools_to_carry"), 8),
        follow_up_questions=_str_list(d.get("follow_up_questions"), 2),
        safe_checks=_str_list(d.get("safe_checks"), 3),
        caller_frustrated=bool(d.get("caller_frustrated", False)),
        owner_reply=str(d.get("owner_reply") or "").strip(),
        technician_brief=str(d.get("technician_brief") or "").strip(),
        caller_language=str(d.get("caller_language") or "hi-en").strip(),
        reasoner=reasoner,
    )
