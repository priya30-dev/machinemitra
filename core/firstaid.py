"""'First-aid while you wait': a few SAFE checks the owner can do before the
technician arrives. Sometimes that alone fixes the problem.

Hard rules, enforced in code on every suggestion (including Evon's):
  - nothing when there is any safety risk (sparks, smoke, gas, shock…)
  - never open panels or covers, touch wires, bypass guards, or reach inside
"""
import re

BLOCKED = [
    "open", "panel cover", "cover", "touch", "wire", "wiring", "terminal", "bypass", "override",
    "guard", "inside", "reach", "hand", "khol", "chhu", "chhoo", "taar", "andar", "haath",
    "खोल", "छू", "तार", "अंदर", "हाथ",
]
MAX_CHECKS = 3

# symptom (as produced by reasoner.fallback) -> {lang: check}
FALLBACK = {
    "machine overheating": {
        "hi-en": "Machine band rakhiye aur coolant ya oil ka level bahar se dekh lijiye.",
        "en-IN": "Keep the machine off and check the coolant or oil level from outside."},
    "abnormal noise": {
        "hi-en": "Machine ko dobara mat chalaiye, isse nuksaan badh sakta hai.",
        "en-IN": "Do not restart the machine; running it can cause more damage."},
    "excessive vibration": {
        "hi-en": "Machine band rakhiye aur dekhiye ki uske neeche ya aas-paas kuch dheela to nahi pada.",
        "en-IN": "Keep it off and look for anything loose lying under or around the machine."},
    "oil or fluid leak": {
        "hi-en": "Leak ke neeche tray rakhiye aur farsh saaf rakhiye taaki koi phisle nahi.",
        "en-IN": "Put a tray under the leak and keep the floor clean so nobody slips."},
    "pressure not building": {
        "hi-en": "Pressure gauge ki reading note kar lijiye, technician ko kaam aayegi.",
        "en-IN": "Note the pressure gauge reading for the technician."},
    "machine not starting or tripping": {
        "hi-en": "Dekhiye ki baaki machines par bijli aa rahi hai ya nahi. Panel mat kholiye.",
        "en-IN": "Check whether other machines have power. Do not open the panel."},
    "controller error or alarm": {
        "hi-en": "Screen par jo error code dikh raha hai uski photo le lijiye.",
        "en-IN": "Take a photo of the error code on the screen."},
}
GENERAL = {
    "hi-en": "Machine ke paas kisi ko mat jaane dijiye aur problem kab shuru hui yeh note kar lijiye.",
    "en-IN": "Keep people away from the machine and note when the problem started.",
}


def is_safe(check: str) -> bool:
    """Reject any suggestion that mentions opening, touching, wires, guards and so on.
    Deliberately strict: a false rejection just means a generic tip is used instead."""
    text = check.lower()
    for word in BLOCKED:
        if (re.search(rf"\b{re.escape(word)}", text) if word.isascii() else word in text):
            return False
    return True


def checks(symptoms: list[str], suggested: list[str], safety_risk: bool, lang: str) -> list[str]:
    """Evon's suggestions if present (filtered by is_safe), else the reviewed rule-based ones."""
    if safety_risk:
        return []
    out = [c for c in suggested if c.strip() and is_safe(c)]
    if not out:
        key = lang if lang in ("hi-en", "en-IN") else ("hi-en" if lang == "hi-IN" else "en-IN")
        out = [FALLBACK[s][key] for s in symptoms if s in FALLBACK] or [GENERAL[key]]
    return out[:MAX_CHECKS]
