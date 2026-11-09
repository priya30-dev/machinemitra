"""Follow-up actions on saved tickets: technician voice updates, the spoken
service report, and voice questions about repair history. Kept outside the UI
so they can be tested."""
from dataclasses import dataclass, field

import config
from core import db, language, matching
from core.pipeline import Result, speak
from gnani import stt
from reasoner import workflows


@dataclass
class ActionResult:
    heard: str = ""
    data: dict = field(default_factory=dict)
    audio: bytes | None = None
    warnings: list[str] = field(default_factory=list)


def _transcribe(audio: bytes | None, text: str | None, languages: str) -> str:
    if text is not None:
        return text
    return stt.transcribe(audio, languages=languages).text


def technician_update(ticket_id: int, audio: bytes | None = None, text: str | None = None,
                      languages: str = "indic-auto", speak_reply: bool = True) -> ActionResult:
    row = db.get_ticket(ticket_id)
    heard = _transcribe(audio, text, languages)
    upd = workflows.tech_update(heard, row.get("ticket") or {}, row["language"])
    r = Result()
    msg = upd.get("owner_message") or workflows.OWNER_MSG.get(upd["status"], "")
    voice = speak(r, msg, row["language"], config.TTS_VOICE_OWNER, "Owner update") if speak_reply else None
    note = upd.get("summary_en", "")
    if upd.get("parts_needed"):
        note += " Parts needed: " + ", ".join(upd["parts_needed"])
    db.set_status(ticket_id, upd["status"], note=f"{note} [{upd.get('engine')}]", audio=voice)
    return ActionResult(heard, upd, voice, r.warnings)


def service_report(ticket_id: int, audio: bytes | None = None, text: str | None = None,
                   languages: str = "indic-auto") -> ActionResult:
    row = db.get_ticket(ticket_id)
    heard = _transcribe(audio, text, languages)
    rep = workflows.service_report(heard, row.get("ticket") or {}, row["language"])
    rep["technician_said"] = heard
    db.save_report(ticket_id, rep)
    db.add_event(ticket_id, "report", "Service report created")
    return ActionResult(heard, rep)


def report_html(ticket_id: int) -> str:
    row = db.get_ticket(ticket_id)
    directory = matching.load_directory()
    fac = next((f["name"] for f in directory["factories"] if f["id"] == row["factory_id"]), row["factory_id"])
    tech = next((t["name"] for t in directory["technicians"] if t["id"] == row["technician_id"]), "—")
    m = db.machine(row["machine_id"]) if row["machine_id"] else None
    return workflows.report_html(row.get("report") or {}, row, m["name"] if m else row["machine_type"], fac, tech)


def ask_history(factory_id: str, audio: bytes | None = None, text: str | None = None,
                languages: str = "indic-auto", machine_id: str | None = None,
                speak_reply: bool = True) -> ActionResult:
    heard = _transcribe(audio, text, languages)
    tickets = db.list_tickets(factory_id=factory_id, limit=60)
    if machine_id:
        tickets = [t for t in tickets if t["machine_id"] == machine_id] or tickets
    lang = language.resolve(heard)
    ans = workflows.answer_history(heard, tickets, lang)
    r = Result()
    voice = speak(r, ans["answer"], lang, config.TTS_VOICE_OWNER, "History answer") if speak_reply else None
    return ActionResult(heard, ans, voice, r.warnings)
