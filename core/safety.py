"""Safety-first check. Runs on the transcript BEFORE any reasoning, using plain
rules, so a danger warning is spoken even if the LLM is slow or offline."""
import re
from dataclasses import dataclass, field

from core.language import safety_alert

# (label, keyword patterns). Latin patterns are matched on word boundaries.
DANGER_SIGNS = [
    ("sparks", ["spark", "sparking", "chingari", "चिंगारी", "स्पार्क"]),
    ("smoke", ["smoke", "dhuan", "dhuaan", "dhua", "धुआं", "धुआँ", "धुंआ"]),
    ("fire", ["fire", "aag", "आग", "flame"]),
    ("burning smell", ["burning smell", "jalne ki smell", "jalne ki badboo", "जलने की"]),
    ("electric shock", ["shock", "current lag", "current maar", "करंट लग", "झटका"]),
    ("gas leak", ["gas leak", "gas ki smell", "gas nikal", "गैस"]),
    ("injury", ["injury", "chot", "चोट", "ghayal", "घायल", "khoon", "खून"]),
    ("explosion risk", ["blast", "explode", "phat", "फट", "धमाका"]),
]


@dataclass
class Danger:
    is_dangerous: bool
    matched: list[str] = field(default_factory=list)


def _found(text: str, pattern: str) -> bool:
    if pattern.isascii():
        return re.search(rf"\b{re.escape(pattern)}", text) is not None
    return pattern in text


def detect_danger(transcript: str) -> Danger:
    text = transcript.lower()
    matched = [label for label, pats in DANGER_SIGNS if any(_found(text, p) for p in pats)]
    return Danger(bool(matched), matched)


def alert_text(language: str) -> str:
    return safety_alert(language)
