"""MachineMitra call pipeline:

  audio ─► Prisma STT ─► noise meter ─► caller language ─► safety check
        ─► Evon ticket (fallback if offline) ─► escalation ─► technician match
        ─► downtime + API cost ─► first-aid checks ─► technician briefing (Evon translation)
        ─► Timbre voice replies ─► saved to SQLite with SLA deadline

Every step records its time and engine for an honest on-screen trace."""
import time
from dataclasses import dataclass, field

import config
from core import budget, costs, db, firstaid, language, matching
from core import escalation as esc_rules
from core import noise as noise_meter
from core.downtime import DowntimeInputs, bump_urgency, cost_per_hour, expected_loss, inr
from core.safety import detect_danger
from gnani import stt, tts
from reasoner import evon, fallback
from reasoner.schema import Ticket

FIRST_AID_INTRO = {"hi-en": "Technician ke aane tak aap yeh kar sakte hain.",
                   "hi-IN": "टेक्नीशियन के आने तक आप यह कर सकते हैं।",
                   "en-IN": "Until the technician arrives, you can do this."}


@dataclass
class Step:
    name: str
    engine: str
    seconds: float
    note: str = ""


@dataclass
class Result:
    transcript: str = ""
    detected_language: str | None = None
    caller_language: str = "hi-en"
    audio_seconds: float = 0.0
    noise: noise_meter.NoiseReading | None = None
    danger: list[str] = field(default_factory=list)
    safety_alert_text: str = ""
    safety_alert_audio: bytes | None = None
    machine: dict | None = None
    ticket: Ticket | None = None
    ticket_id: int | None = None
    escalation: esc_rules.Escalation | None = None
    cost_per_hour: float = 0.0
    expected_loss: float = 0.0
    match: matching.Match | None = None
    alternatives: list[matching.Match] = field(default_factory=list)
    repeat_count: int = 1
    repeat_note: str = ""
    first_aid: list[str] = field(default_factory=list)
    first_aid_audio: bytes | None = None
    owner_reply_text: str = ""
    owner_reply_audio: bytes | None = None
    tech_brief_text: str = ""
    tech_brief_language: str = "en-IN"
    tech_brief_audio: bytes | None = None
    api_cost: float = 0.0
    seconds_to_ticket: float = 0.0
    steps: list[Step] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    _tts_chars: int = 0
    _stt_seconds: float = 0.0


def _timed(result: Result, name: str, engine: str, fn, note: str = ""):
    t0 = time.time()
    out = fn()
    result.steps.append(Step(name, engine, round(time.time() - t0, 2), note))
    return out


def speak(result: Result, text: str, lang: str, voice: str, label: str = "Voice reply") -> bytes | None:
    """Timbre with a cache: the same sentence in the same voice is never paid for twice."""
    if not text.strip():
        return None
    key = budget.cache_key("tts", config.TTS_MODEL, text, lang, voice)
    cached = budget.cache_get(key)
    if cached:
        result.steps.append(Step(label, "Gnani Timbre (cached)", 0.0))
        return cached
    try:
        audio = _timed(result, label, f"Gnani Timbre {config.TTS_MODEL}", lambda: tts.synthesize(text, lang, voice),
                       note=f"{len(text)} chars, {lang}")
        budget.cache_put(key, audio)
        result._tts_chars += len(text)
        return audio
    except Exception as e:  # a voice failure should never lose the ticket
        result.warnings.append(f"{label} failed: {getattr(e, 'friendly', e)}")
        return None


def repeat_note(count: int, machine_type: str) -> str:
    if count >= 3:
        return (f"This is breakdown number {count} for this {machine_type} in 30 days. "
                "Recommend a preventive maintenance visit instead of another quick fix.")
    if count == 2:
        return f"Second {machine_type} breakdown in 30 days. Check whether the last repair held."
    return ""


def make_ticket(transcript: str, context: str, result: Result) -> Ticket:
    if config.EVON_BASE_URL:
        try:
            return _timed(result, "Diagnosis & ticket", "Gnani Evon v3.3",
                          lambda: evon.make_ticket(transcript, context))
        except evon.EvonUnavailable as e:
            result.warnings.append(f"Evon unavailable ({str(e)[:80]}). Used rule-based fallback.")
    return _timed(result, "Diagnosis & ticket", "Rule-based fallback",
                  lambda: fallback.make_ticket(transcript, context))


def briefing(ticket: Ticket, match: matching.Match | None, factory: dict, machine: dict | None,
             result: Result) -> tuple[str, str]:
    """Technician brief in the technician's own language when Evon can translate."""
    base = ticket.technician_brief or f"{ticket.machine_type} fault at {factory['name']}."
    if machine:
        base += f" Machine: {machine['name']} ({machine['model']}, installed {machine['installed']})."
    if match:
        base += f" Location: {factory['name']}, about {match.distance_km} km away."
    target = match.technician["language"] if match else "en-IN"
    if target in ("en-IN", "hi-en"):
        return base, target
    if ticket.reasoner == "evon":
        try:
            text = _timed(result, "Technician briefing", "Gnani Evon v3.3",
                          lambda: evon.translate(base, target), note=f"translated to {target}")
            return text, target
        except evon.EvonUnavailable as e:
            result.warnings.append(f"Briefing translation failed ({str(e)[:60]}); sent in English.")
    else:
        result.warnings.append(f"Technician prefers {language.NAMES.get(target, target)}; "
                               "translation needs Evon, so the brief is in English.")
    return base, "en-IN"


def run(audio: bytes | None, suffix: str, factory: dict, downtime: DowntimeInputs,
        transcript_override: str | None = None, extra_context: str = "", telephony: bool = False,
        speak_replies: bool = True, languages: str | None = None, stt_format: str = "codemix",
        machine_id: str | None = None, detected_language: str | None = None, save: bool = True,
        streamed_seconds: float = 0.0, update_ticket_id: int | None = None) -> Result:
    result = Result()
    t_start = time.time()
    languages = languages or config.STT_LANGUAGES

    # 1. Speech to text (Prisma). Skipped when a transcript is supplied (streaming mode, samples, tests).
    if transcript_override is not None:
        result.transcript, result.detected_language = transcript_override, detected_language
        result._stt_seconds = result.audio_seconds = streamed_seconds  # billed by the streaming call
    else:
        key = budget.cache_key("stt", audio, suffix, telephony, languages, stt_format)
        tr = budget.cache_get(key)
        if tr:
            result.steps.append(Step("Speech to text", "Gnani Prisma (cached)", 0.0))
        else:
            tr = _timed(result, "Speech to text", f"Gnani Prisma {config.STT_MODEL}",
                        lambda: stt.transcribe(audio, suffix=suffix, languages=languages,
                                               output_format=stt_format, telephony=telephony),
                        note=f"languages: {languages}")
            budget.cache_put(key, tr)
            result._stt_seconds = tr.audio_seconds
        result.transcript, result.detected_language, result.audio_seconds = tr.text, tr.language, tr.audio_seconds

    # 2. Noise meter
    if audio:
        result.noise = noise_meter.estimate(audio, telephony)

    if not result.transcript.strip():
        result.warnings.append("No speech was detected in the audio.")
        return result

    # 3. Caller language, then the safety check (rules, instant, before any AI)
    lang = language.resolve(result.transcript, result.detected_language)
    result.caller_language = lang
    danger = detect_danger(result.transcript)
    result.danger = danger.matched
    if danger.is_dangerous:
        result.safety_alert_text = language.safety_alert(lang)
        if speak_replies:
            result.safety_alert_audio = speak(result, result.safety_alert_text, lang, config.TTS_VOICE_OWNER,
                                              "Safety alert")

    # 4. Machine context from a QR sticker, if any
    machine = db.machine(machine_id) if machine_id else None
    result.machine = machine
    context = extra_context
    if machine:
        context += (f" The caller scanned the QR sticker of '{machine['name']}', a {machine['machine_type']} "
                    f"({machine['model']}, installed {machine['installed']}).")
    per_hour = cost_per_hour(downtime)
    if per_hour:
        context += f" Downtime costs the owner about {inr(per_hour)} per hour."

    # 5. Diagnosis (Evon, or fallback)
    ticket = make_ticket(result.transcript, context.strip(), result)
    if machine and ticket.machine_type in ("unknown", "unknown machine"):
        ticket.machine_type = machine["machine_type"]
        ticket.follow_up_questions = [q for q in ticket.follow_up_questions if "machine" not in q.lower()]
    if ticket.reasoner != "evon" or ticket.caller_language not in language.NAMES:
        ticket.caller_language = lang
    lang = result.caller_language = ticket.caller_language
    if danger.is_dangerous:  # rules can only raise safety, never lower it
        ticket.safety_risk, ticket.urgency = True, "critical"
        ticket.safety_reason = ticket.safety_reason or ", ".join(danger.matched)
    ticket.urgency = bump_urgency(ticket.urgency, per_hour)

    # 6. Escalation
    repeat = db.open_ticket_for(factory["id"], machine_id, ticket.machine_type) if save else None
    if repeat and repeat["id"] == update_ticket_id:  # answering our own follow-up is not a repeat call
        repeat = None
    esc = esc_rules.detect(result.transcript, ticket.caller_frustrated, repeat)
    result.escalation = esc
    if esc.escalate:
        ticket.urgency = esc_rules.raise_urgency(ticket.urgency)
    result.ticket = ticket

    # 7. Technician match + downtime cost
    directory = matching.load_directory()
    ranked = matching.rank(ticket.skills_required, factory, directory["technicians"])
    best = esc_rules.pick_senior(ranked) if esc.escalate else (ranked[0] if ranked else None)
    result.match = best
    result.alternatives = [m for m in ranked if m is not best][:2]
    result.cost_per_hour = per_hour
    if best:
        result.expected_loss = expected_loss(downtime, best.eta_hours)
    else:
        result.warnings.append("No technician with matching skills is available right now.")

    # 8. First-aid while you wait
    result.first_aid = firstaid.checks(ticket.symptoms, ticket.safe_checks, ticket.safety_risk, lang)

    # 9. Replies in the caller's language
    reply = ticket.owner_reply if ticket.reasoner == "evon" and ticket.owner_reply else language.ack(lang)
    if best:
        reply += " " + language.eta_sentence(lang, best.technician["name"].split()[0], best.eta_hours)
    if ticket.follow_up_questions:
        reply += " " + ticket.follow_up_questions[0]
    result.owner_reply_text = reply
    result.tech_brief_text, result.tech_brief_language = briefing(ticket, best, factory, machine, result)
    result.seconds_to_ticket = round(time.time() - t_start, 1)

    if speak_replies:
        result.owner_reply_audio = speak(result, reply, lang, config.TTS_VOICE_OWNER, "Owner reply")
        if result.first_aid:
            intro = FIRST_AID_INTRO.get(lang, "")
            result.first_aid_audio = speak(result, (intro + " " + " ".join(result.first_aid)).strip(), lang,
                                           config.TTS_VOICE_OWNER, "First-aid tips")
        result.tech_brief_audio = speak(result, result.tech_brief_text, result.tech_brief_language,
                                        config.TTS_VOICE_TECH, "Technician briefing")
    result.api_cost = costs.call_cost(result._stt_seconds, result._tts_chars)

    # 10. Save with SLA deadline; repeat-fault memory
    if save and update_ticket_id:
        db.update_ticket(update_ticket_id, ticket=ticket.to_dict(), transcript=result.transcript,
                         technician_id=best.technician["id"] if best else None, language=lang,
                         cost_per_hour=per_hour, expected_loss=result.expected_loss, api_cost=result.api_cost,
                         escalated=esc.escalate, escalation_reason=esc.reason,
                         note="Caller answered follow-up questions")
        result.ticket_id = update_ticket_id
    elif save:
        result.ticket_id = db.create_ticket(
            factory_id=factory["id"], machine_id=machine_id, ticket=ticket.to_dict(), transcript=result.transcript,
            technician_id=best.technician["id"] if best else None, language=lang, cost_per_hour=per_hour,
            expected_loss=result.expected_loss, api_cost=result.api_cost,
            snr_db=result.noise.snr_db if result.noise else None, seconds_to_ticket=result.seconds_to_ticket,
            escalated=esc.escalate, escalation_reason=esc.reason)
    if save:
        if result.tech_brief_audio:
            db.add_event(result.ticket_id, "briefing", result.tech_brief_text, result.tech_brief_audio)
        if result.owner_reply_audio:
            db.add_event(result.ticket_id, "owner_reply", reply, result.owner_reply_audio)
        result.repeat_count = len(db.recent_for_machine(factory["id"], machine_id, ticket.machine_type))
        result.repeat_note = repeat_note(result.repeat_count, ticket.machine_type)
    return result
