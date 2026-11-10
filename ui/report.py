"""Tab 1 — the owner reports a breakdown by voice."""
import subprocess

import streamlit as st

import config
from core import budget, db, language, pipeline
from core.downtime import inr
from gnani import stt_stream
from gnani.audio import duration_seconds
from gnani.errors import GnaniError
from ui.common import audio_suffix, can_go_live, nice, note_live_run, pill, urgency_pill

SAMPLES = {
    "CNC spindle overheating (Hinglish)": dict(machine="M1", lang=None, text=(
        "Hello bhaiya, humari CNC machine ka spindle bahut garam ho raha hai aur ajeeb si awaaz aa rahi hai. "
        "Subah se production ruka hua hai, jaldi kisi ko bhejiye.")),
    "Hydraulic press leaking (Hinglish)": dict(machine="M3", lang=None, text=(
        "Hydraulic press mein neeche se oil leak ho raha hai aur pressure nahi ban raha. Do din se aisa hai.")),
    "Panel sparking — safety case": dict(machine="M4", lang=None, text=(
        "Sir, motor ke panel se chingari nikal rahi hai aur jalne ki smell aa rahi hai, kya karein?")),
    "Angry repeat call — escalation": dict(machine="M2", lang=None, text=(
        "Kitni baar bolu, compressor phir se band ho gaya hai aur abhi tak koi nahi aaya!")),
    "Tamil caller — regional reply": dict(machine="M1", lang="ta-IN", text=(
        "CNC மெஷின் ஸ்பிண்டில் ரொம்ப சூடாகுது, சத்தமும் வருது. உற்பத்தி நின்றுவிட்டது.")),
}


def _pcm16k(raw: bytes, telephony: bool) -> bytes:
    filters = "aresample=8000,aresample=16000" if telephony else "aresample=16000"
    return subprocess.run(["ffmpeg", "-v", "error", "-i", "pipe:0", "-af", filters, "-ac", "1", "-f", "s16le",
                           "pipe:1"], input=raw, capture_output=True, check=True).stdout


def _stream_transcribe(raw: bytes, settings: dict) -> tuple[str, str | None, float]:
    """Stream through Prisma's realtime API and show each phrase as it is recognised."""
    pcm = _pcm16k(raw, settings["telephony"])
    box = st.empty()
    phrases, lang = [], None
    box.markdown('<div class="live-box">Listening through Prisma realtime…</div>', unsafe_allow_html=True)
    for msg in stt_stream.stream_pcm(pcm, settings["languages"]):
        kind = msg.get("type")
        if kind == "speech_start":
            box.markdown(f'<div class="live-box">{" ".join(phrases)} <i>…speaking</i></div>', unsafe_allow_html=True)
        elif kind == "transcript" and msg.get("text"):
            phrases.append(msg["text"].strip())
            lang = lang or msg.get("detected_language_code")
            box.markdown(f'<div class="live-box">{" ".join(phrases)}</div>', unsafe_allow_html=True)
        elif kind == "error":
            st.warning(f"Prisma realtime: {msg.get('message')}")
    return " ".join(phrases), lang, round(len(pcm) / 32000, 1)


def _run(settings: dict, *, audio=None, suffix=".wav", transcript=None, detected=None, machine_id=None,
         streamed_seconds=0.0, extra_context="", update_ticket_id=None):
    with st.status("Working on your call…", expanded=False) as status:
        try:
            res = pipeline.run(audio, suffix, settings["factory"], settings["downtime"],
                               transcript_override=transcript, detected_language=detected,
                               extra_context=extra_context, telephony=settings["telephony"],
                               speak_replies=settings["speak"] and not config.DEMO_MODE,
                               languages=settings["languages"], machine_id=machine_id,
                               streamed_seconds=streamed_seconds, update_ticket_id=update_ticket_id)
        except GnaniError as e:
            status.update(label="Gnani API error", state="error")
            st.error(e.friendly)
            return
        except Exception as e:
            status.update(label="Something went wrong", state="error")
            st.error(f"Unexpected error: {e}")
            return
        status.update(label=f"Ticket #{res.ticket_id} created", state="complete")
    st.session_state["result"] = res


def _show(r: pipeline.Result):
    for w in r.warnings:
        st.info(w)
    if not r.ticket:
        return
    t = r.ticket

    if r.danger:
        st.error(f"**Safety alert — {', '.join(r.danger)} reported.** {r.safety_alert_text}")
        if r.safety_alert_audio:
            st.audio(r.safety_alert_audio, format="audio/wav", autoplay=True)
    if r.escalation and r.escalation.escalate:
        st.warning(f"**Escalated:** {r.escalation.reason}. Sent to the most senior matching technician.")

    tags = urgency_pill(t.urgency)
    tags += pill("Diagnosis: " + ("Gnani Evon v3.3" if t.reasoner == "evon" else "Rule-based fallback"), "eng")
    tags += pill("Caller language: " + language.NAMES.get(r.caller_language, r.caller_language), "eng")
    if r.noise:
        tags += pill("" + r.noise.label, f"n-{r.noise.level}")
    if r.machine:
        tags += pill(f"{r.machine['name']}", "eng")

    col1, col2 = st.columns([3, 2], gap="large")
    with col1:
        st.markdown(f"### Ticket #{r.ticket_id} · {nice(t.machine_type)}")
        st.markdown(tags, unsafe_allow_html=True)
        if t.urgency_reason:
            st.caption(t.urgency_reason)
        if t.symptoms:
            st.markdown("**Symptoms:** " + ", ".join(t.symptoms))
        if t.probable_causes:
            st.markdown("**Likely causes**")
            for c in t.probable_causes:
                st.markdown(f"- {c.cause} · _{c.confidence} confidence_")
        a, b = st.columns(2)
        a.markdown("**Parts to carry**\n" + "\n".join(f"- {p}" for p in t.parts_to_carry or ["—"]))
        b.markdown("**Tools**\n" + "\n".join(f"- {p}" for p in t.tools_to_carry or ["—"]))
        if r.repeat_note:
            st.warning("" + r.repeat_note)

    with col2:
        st.markdown("##### Cost & impact")
        m1, m2 = st.columns(2)
        m1.metric("Downtime cost", f"{inr(r.cost_per_hour)}/hr")
        m2.metric("Loss until arrival", inr(r.expected_loss) if r.match else "—")
        m3, m4 = st.columns(2)
        m3.metric("API cost of this call", f"₹{r.api_cost:.2f}")
        m4.metric("Call → ticket", f"{r.seconds_to_ticket:.1f} s")
        if r.cost_per_hour and r.api_cost:
            st.caption(f"Every hour saved is worth about {int(r.cost_per_hour / max(r.api_cost, 0.01)):,}× "
                       "this call's API cost.")
        if r.match:
            tech = r.match.technician
            st.markdown(
                f'<div class="mm-card"><b>{tech["name"]}</b> · {tech["rating"]}<br>'
                f'Skills: {", ".join(tech["skills"])}<br>{r.match.distance_km} km away · ETA ~{r.match.eta_hours} h'
                f'<br>Speaks: {language.NAMES.get(tech["language"], tech["language"])}</div>',
                unsafe_allow_html=True)
            if r.alternatives:
                st.caption("Backup: " + ", ".join(f'{m.technician["name"]} ({m.eta_hours} h)' for m in r.alternatives))
        st.caption("Technicians are fictional demo data.")

    st.markdown("#### What the owner hears")
    st.write(r.owner_reply_text)
    if r.owner_reply_audio:
        st.audio(r.owner_reply_audio, format="audio/wav", autoplay=not r.danger)
    if r.first_aid:
        st.markdown("#### While you wait — safe checks")
        for c in r.first_aid:
            st.markdown(f"- {c}")
        if r.first_aid_audio:
            st.audio(r.first_aid_audio, format="audio/wav")
        st.caption("Only checks that need no tools, no opening panels and no touching parts.")
    st.markdown(f"#### Technician briefing ({language.NAMES.get(r.tech_brief_language, r.tech_brief_language)})")
    st.write(r.tech_brief_text)
    if r.tech_brief_audio:
        st.audio(r.tech_brief_audio, format="audio/wav")

    with st.expander("Transcript and pipeline trace"):
        st.markdown(f"**Prisma transcript** (detected: {r.detected_language or 'not reported'}, "
                    f"{r.audio_seconds}s audio)")
        st.code(r.transcript, language=None)
        st.table([{"step": s.name, "engine": s.engine, "seconds": s.seconds, "note": s.note} for s in r.steps])
        st.json(t.to_dict(), expanded=False)


def render(settings: dict, machine_from_qr: str | None):
    ss = st.session_state
    factory = settings["factory"]
    machines = db.machines(factory["id"])
    ids = [None] + [m["id"] for m in machines]
    default = ids.index(machine_from_qr) if machine_from_qr in ids else 0
    if machine_from_qr and default:
        st.success(f"Machine from QR sticker: **{db.machine(machine_from_qr)['name']}**. Just describe the problem.")

    left, right = st.columns([1, 1], gap="large")
    with left:
        st.subheader("Report a breakdown")
        machine_id = st.selectbox("Machine (optional — or scan its QR sticker)", ids, index=default,
                                  format_func=lambda i: "Not sure / other" if i is None else db.machine(i)["name"])
        streaming = st.toggle("Streaming transcription (Prisma realtime API)", value=True,
                              help="Streams your recording through Prisma's WebSocket API at speaking speed; "
                                   "each phrase appears as soon as Prisma recognises it.")
        rec = st.audio_input("Speak like you would on a phone call (up to 60 seconds)")
        up = st.file_uploader("…or upload a call recording", type=["wav", "mp3", "m4a", "ogg", "flac", "aac"])
        src = rec or up
        if src is not None:
            raw, suffix = src.getvalue(), audio_suffix(src)
            key = budget.cache_key(raw)
            try:
                secs = duration_seconds(raw, suffix)
            except Exception:
                secs = 0
            if secs > config.MAX_AUDIO_SECONDS:
                st.error(f"That recording is {secs:.0f}s. Please keep it under {config.MAX_AUDIO_SECONDS}s.")
            elif st.button("Send to MachineMitra", type="primary", disabled=key == ss.get("last_audio_key")):
                if can_go_live():
                    ss["last_audio_key"] = key
                    note_live_run()
                    if streaming:
                        try:
                            text, detected, streamed = _stream_transcribe(raw, settings)
                        except Exception as e:
                            st.warning(f"Realtime streaming failed ({e}); using the standard API instead.")
                            _run(settings, audio=raw, suffix=suffix, machine_id=machine_id)
                        else:
                            _run(settings, audio=raw, suffix=suffix, transcript=text, detected=detected,
                                 machine_id=machine_id, streamed_seconds=streamed)
                    else:
                        _run(settings, audio=raw, suffix=suffix, machine_id=machine_id)
    with right:
        st.subheader("Or try a sample call")
        st.caption("Samples skip speech-to-text and don't use your live runs.")
        choice = st.selectbox("Sample", list(SAMPLES), label_visibility="collapsed")
        sample = SAMPLES[choice]
        st.text_area("Transcript", sample["text"], height=110, disabled=True, key=f"s_{choice}")
        if st.button("Run sample"):
            sample_factory = next(f for f in settings["directory"]["factories"]
                                  if f["id"] == db.machine(sample["machine"])["factory_id"])
            _run({**settings, "factory": sample_factory}, transcript=sample["text"], detected=sample["lang"],
                 machine_id=sample["machine"])

    r = ss.get("result")
    if r:
        st.divider()
        _show(r)
        if r.ticket and r.ticket.follow_up_questions and r.ticket_id:
            st.markdown("#### Follow-up")
            st.write(" · ".join(r.ticket.follow_up_questions))
            answer = st.audio_input("Answer by voice", key=f"followup_{r.ticket_id}")
            if answer is not None and st.button("Update ticket with answer") and can_go_live():
                from gnani import stt
                note_live_run()
                try:
                    extra = stt.transcribe(answer.getvalue(), languages=settings["languages"]).text
                except GnaniError as e:
                    st.error(e.friendly)
                else:
                    _run(settings, transcript=r.transcript + " " + extra, detected=r.detected_language,
                         machine_id=r.machine["id"] if r.machine else None,
                         extra_context="The caller answered the follow-up questions.",
                         update_ticket_id=r.ticket_id)
                    st.rerun()
