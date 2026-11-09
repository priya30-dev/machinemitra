"""Frustration detection and escalation — call-centre intelligence.

Escalate when the caller sounds frustrated, or calls again about a machine
that already has an unfixed ticket from the last day. Escalated tickets go to
the highest-rated matching technician and are at least 'high' urgency."""
import re
from dataclasses import dataclass

FRUSTRATION = [
    "kitni baar", "kab se", "abhi tak nahi", "abhi tak koi", "phir se", "dobara", "pagal", "bakwas",
    "bekaar", "faltu", "jaldi karo", "gussa", "koi nahi aaya", "again", "still not", "nobody came",
    "worst", "useless", "kitna wait", "कितनी बार", "अभी तक", "फिर से", "बकवास", "कोई नहीं आया", "गुस्सा",
]


@dataclass
class Escalation:
    escalate: bool
    reason: str = ""


def detect(transcript: str, llm_frustrated: bool = False, repeat_ticket: dict | None = None) -> Escalation:
    text = transcript.lower()
    hits = [w for w in FRUSTRATION if (re.search(rf"\b{re.escape(w)}\b", text) if w.isascii() else w in text)]
    reasons = []
    if repeat_ticket:
        reasons.append(f"repeat call — ticket #{repeat_ticket['id']} for this machine is still {repeat_ticket['status']}")
    if hits:
        reasons.append("caller sounds frustrated (" + ", ".join(hits[:3]) + ")")
    elif llm_frustrated:
        reasons.append("caller sounds frustrated (Evon)")
    return Escalation(bool(reasons), "; ".join(reasons))


def raise_urgency(urgency: str) -> str:
    return urgency if urgency == "critical" else "high"


def pick_senior(ranked: list) -> object | None:
    """Among the best skill matches, prefer the highest rating."""
    if not ranked:
        return None
    top_overlap = len(ranked[0].skill_overlap)
    pool = [m for m in ranked[:4] if len(m.skill_overlap) == top_overlap]
    return max(pool, key=lambda m: m.technician.get("rating", 0))
