"""Rule-based ticket builder used when the Evon server is offline.

It is deliberately simple and the UI labels its tickets as "fallback" so the
demo never pretends rules are AI. Keywords cover Latin script and Devanagari,
because Prisma's codemix output keeps Hindi words in Devanagari."""
from core.safety import detect_danger
from reasoner.schema import Cause, Ticket

MACHINES = {
    "CNC machine": ["cnc", "सीएनसी", "vmc", "turning centre"],
    "lathe": ["lathe", "खराद", "लेथ"],
    "air compressor": ["compressor", "कंप्रेसर", "कम्प्रेसर"],
    "hydraulic press": ["hydraulic", "हाइड्रोलिक", "press machine", "power press", "प्रेस"],
    "conveyor": ["conveyor", "कन्वेयर", "belt", "बेल्ट"],
    "electric motor": ["motor", "मोटर"],
    "injection moulding machine": ["injection", "moulding", "molding", "मोल्डिंग"],
    "welding machine": ["welding", "वेल्डिंग"],
    "pump": ["pump", "पंप"],
    "boiler": ["boiler", "बॉयलर"],
}

# symptom key -> (keywords, English symptom, causes, skills, parts, tools)
SYMPTOMS = {
    "overheating": (["garam", "गरम", "गर्म", "heat", "overheat", "very hot", "तप रह"],
                    "machine overheating",
                    ["worn or dry bearings", "cooling fan or coolant failure", "overload"],
                    ["mechanical"], ["bearings", "grease", "coolant"], ["infrared thermometer"]),
    "noise": (["awaaz", "aawaz", "awaz", "आवाज़", "आवाज", "noise", "sound", "khat khat", "खट"],
              "abnormal noise",
              ["bearing damage", "loose or misaligned parts", "gear wear"],
              ["mechanical"], ["bearings", "belts"], ["stethoscope", "spanner set"]),
    "vibration": (["vibration", "vibrate", "hil raha", "hil rahi", "हिल रह", "kaamp", "कांप", "कंपन"],
                  "excessive vibration",
                  ["imbalance or misalignment", "loose foundation bolts", "bearing wear"],
                  ["mechanical"], ["bearings", "foundation bolts"], ["dial indicator", "spanner set"]),
    "leak": (["leak", "लीक", "tapak", "टपक", "oil nikal", "तेल"],
             "oil or fluid leak",
             ["damaged seal or O-ring", "loose hose fitting"],
             ["hydraulic"], ["seal kit", "O-rings", "hydraulic oil"], ["spanner set"]),
    "pressure": (["pressure", "प्रेशर", "dabav", "दबाव"],
                 "pressure not building",
                 ["internal leak or worn pump", "faulty relief valve", "air in the line"],
                 ["hydraulic"], ["relief valve", "seal kit"], ["pressure gauge"]),
    "not_starting": (["start nahi", "स्टार्ट नहीं", "chal nahi", "चल नहीं", "band ho", "बंद हो",
                      "not start", "won't start", "trip"],
                     "machine not starting or tripping",
                     ["tripped MCB or blown fuse", "faulty contactor", "motor winding fault"],
                     ["electrical"], ["fuses", "contactor", "MCB"], ["multimeter", "clamp meter"]),
    "electrical": (["spark", "स्पार्क", "chingari", "चिंगारी", "current", "करंट", "short", "शॉर्ट",
                    "wire", "वायर", "burning smell", "jal raha", "jal rahi", "जल रह"],
                   "electrical fault signs",
                   ["insulation failure or short circuit", "loose terminal"],
                   ["electrical"], ["cable lugs", "insulation tape", "fuses"], ["multimeter", "insulation tester"]),
    "error_code": (["error", "एरर", "alarm", "अलार्म", "display", "screen", "plc"],
                   "controller error or alarm",
                   ["controller or sensor fault", "parameter or program error"],
                   ["plc_electronics", "cnc"], ["sensor"], ["laptop with controller software"]),
}

STOPPED_WORDS = ["ruka", "रुका", "ruk gaya", "रुक गया", "band hai", "बंद है", "production",
                 "प्रोडक्शन", "stopped", "kaam nahi", "काम नहीं"]


def _has(text: str, words: list[str]) -> bool:
    return any(w in text for w in words)


def make_ticket(transcript: str, context: str = "") -> Ticket:
    text = transcript.lower()
    machine = next((m for m, kws in MACHINES.items() if _has(text, kws)), "unknown machine")

    symptoms, causes, skills, parts, tools = [], [], [], [], []
    for kws, symptom, cs, sk, pt, tl in SYMPTOMS.values():
        if _has(text, kws):
            symptoms.append(symptom)
            causes += [c for c in cs if c not in causes]
            skills += [s for s in sk if s not in skills]
            parts += [p for p in pt if p not in parts]
            tools += [t for t in tl if t not in tools]
    if machine == "CNC machine":  # CNC faults go to a CNC specialist first
        skills = ["cnc"] + [s for s in skills if s in ("plc_electronics", "electrical")]

    danger = detect_danger(transcript)
    stopped = _has(text, STOPPED_WORDS)
    if danger.is_dangerous:
        urgency, reason = "critical", f"Possible safety hazard: {', '.join(danger.matched)}."
    elif stopped:
        urgency, reason = "high", "Caller says production has stopped."
    elif symptoms:
        urgency, reason = "medium", "Machine running with a reported fault."
    else:
        urgency, reason = "medium", "Not enough detail to judge urgency."

    questions = []
    if machine == "unknown machine":
        questions.append("Kaunsi machine kharab hui hai?")
    if not symptoms:
        questions.append("Machine mein kya problem dikh rahi hai — awaaz, garmi, leak ya band ho gayi?")

    reply = ("Aapki shikayat mil gayi hai. Hum technician bhej rahe hain."
             if not danger.is_dangerous else
             "Machine ka power turant band kijiye aur machine se door rahiye. Hum technician bhej rahe hain.")
    brief = (f"{machine[:1].upper() + machine[1:]} reported. Symptoms: {', '.join(symptoms) or 'not clear'}. "
             f"Urgency {urgency}. Carry: {', '.join(parts[:4]) or 'standard kit'}.")

    return Ticket(
        machine_type=machine, symptoms=symptoms,
        probable_causes=[Cause(c, "low") for c in causes[:4]],
        urgency=urgency, urgency_reason=reason,
        safety_risk=danger.is_dangerous, safety_reason=", ".join(danger.matched),
        skills_required=skills or ["mechanical"], parts_to_carry=parts[:8], tools_to_carry=tools[:8],
        follow_up_questions=questions[:2], owner_reply=reply, technician_brief=brief,
        caller_language="hi-en", reasoner="fallback",
    )
