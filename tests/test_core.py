"""Unit tests. Gnani and Evon are mocked, so these cost no credits.
Run:  python -m pytest -q"""
import json
import os
import subprocess
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import config  # noqa: E402
from core import downtime, matching, pipeline, safety  # noqa: E402
from gnani import audio, errors, stt, tts  # noqa: E402
from reasoner import evon, fallback, schema  # noqa: E402

FACTORY = {"id": "F1", "name": "Demo factory", "lat": 27.2046, "lon": 78.0350}


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "CACHE_DIR", str(tmp_path))
    monkeypatch.setattr(config, "GNANI_API_KEY", "test-key")
    monkeypatch.setattr(config, "EVON_BASE_URL", "")


class FakeResp:
    def __init__(self, status=200, body=None, content=b""):
        self.status_code, self._body, self.content = status, body, content
        self.text = json.dumps(body) if body is not None else ""

    def json(self):
        if self._body is None:
            raise ValueError
        return self._body


def tone_wav(seconds: float) -> bytes:
    out = subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", f"sine=frequency=440:duration={seconds}",
                          "-ac", "1", "-ar", "16000", "-f", "wav", "-"], capture_output=True, check=True)
    return out.stdout


# ---------- safety ----------
def test_safety_detects_hinglish_and_devanagari():
    assert safety.detect_danger("motor se chingari nikal rahi hai").matched == ["sparks"]
    assert "smoke" in safety.detect_danger("पैनल से धुआं आ रहा है").matched
    assert not safety.detect_danger("spindle garam ho raha hai, jaldi aao").is_dangerous


# ---------- fallback reasoner ----------
def test_fallback_cnc_overheating():
    t = fallback.make_ticket("CNC machine ka spindle bahut garam ho raha hai aur awaaz aa rahi hai, production ruka hua hai")
    assert t.machine_type == "CNC machine"
    assert "machine overheating" in t.symptoms and "abnormal noise" in t.symptoms
    assert t.urgency == "high" and "cnc" in t.skills_required and t.reasoner == "fallback"


def test_fallback_no_false_heat_from_hota():
    t = fallback.make_ticket("compressor chalu hota hai par pressure nahi banta")
    assert "machine overheating" not in t.symptoms
    assert t.machine_type == "air compressor" and "pressure not building" in t.symptoms


def test_fallback_safety_is_critical():
    t = fallback.make_ticket("panel mein spark aa raha hai")
    assert t.urgency == "critical" and t.safety_risk


# ---------- schema / JSON parsing ----------
def test_extract_json_with_fences_and_chatter():
    assert evon.extract_json('Sure!\n```json\n{"a": {"b": 1}}\n```') == {"a": {"b": 1}}
    with pytest.raises(ValueError):
        evon.extract_json("no json here")


def test_schema_coerces_bad_values():
    t = schema.from_dict({"urgency": "EXTREME", "skills_required": ["Electrical", "magic"],
                          "probable_causes": ["loose wire", {"cause": "x", "confidence": "sure"}]}, "evon")
    assert t.urgency == "medium" and t.skills_required == ["electrical"]
    assert t.probable_causes[1].confidence == "medium"


# ---------- downtime + matching ----------
def test_inr_grouping_and_cost():
    assert downtime.inr(1234567) == "₹12,34,567" and downtime.inr(999) == "₹999"
    d = downtime.DowntimeInputs(idle_workers=6, wage_per_hour=100, lost_output_per_hour=3000)
    assert downtime.cost_per_hour(d) == 3600
    assert downtime.bump_urgency("medium", 6000) == "high"
    assert downtime.bump_urgency("critical", 0) == "critical"


def test_matching_prefers_skill_and_skips_unavailable():
    techs = matching.load_directory()["technicians"]
    ranked = matching.rank(["hydraulic"], FACTORY, techs)
    assert ranked[0].technician["id"] in ("T3", "T6")
    assert all(m.technician["available"] for m in ranked)


# ---------- audio chunking ----------
def test_chunks_long_audio_under_30s():
    chunks = audio.to_wav_chunks(tone_wav(65))
    assert len(chunks) == 3
    assert all(audio.duration_seconds(c) <= 29 for c in chunks)


# ---------- Gnani clients (mocked HTTP) ----------
def test_stt_sends_documented_fields(monkeypatch):
    calls = []

    def fake_post(url, **kw):
        calls.append((url, kw))
        return FakeResp(body={"success": True, "transcript": "spindle garam hai", "detected_language_code": "hi-IN"})

    monkeypatch.setattr(errors.requests, "post", fake_post)
    tr = stt.transcribe(tone_wav(3))
    url, kw = calls[0]
    assert url.endswith("/stt/v3") and kw["headers"]["X-API-Key-ID"] == "test-key"
    assert kw["data"]["model"] == "prisma-v3.0" and kw["data"]["language_code"] == "hi-IN,en-IN"
    assert "audio_file" in kw["files"] and tr.text == "spindle garam hai"


def test_stt_error_shapes(monkeypatch):
    monkeypatch.setattr(errors.requests, "post", lambda url, **kw: FakeResp(
        401, {"detail": {"error_code": "INVALID_API_KEY", "message": "Unauthorized", "status_code": 401}}))
    with pytest.raises(errors.GnaniError) as e:
        stt.transcribe(tone_wav(2))
    assert e.value.code == "INVALID_API_KEY" and "invalid" in e.value.friendly


def test_tts_body(monkeypatch):
    seen = {}

    def fake_post(url, **kw):
        seen.update(url=url, **kw)
        return FakeResp(content=b"RIFFfake")

    monkeypatch.setattr(errors.requests, "post", fake_post)
    assert tts.synthesize("Namaste", "xx-YY", speed=2) == b"RIFFfake"
    body = seen["json"]
    assert seen["url"].endswith("/api/v1/tts/inference")
    assert body["model"] == "timbre-v3.0" and body["language"] == "auto" and body["speed"] == 1.15


# ---------- full pipeline ----------
def test_pipeline_fallback_end_to_end(monkeypatch):
    monkeypatch.setattr(pipeline.tts, "synthesize", lambda text, lang, voice: b"WAV")
    r = pipeline.run(None, ".wav", FACTORY, downtime.DowntimeInputs(5, 100, 2000),
                     transcript_override="hydraulic press mein oil leak hai aur pressure nahi ban raha, production ruka hai")
    assert r.ticket.reasoner == "fallback" and r.ticket.urgency == "high"
    assert r.match and "hydraulic" in r.match.skill_overlap
    assert r.cost_per_hour == 2500 and r.owner_reply_audio == b"WAV"
    assert "ji lagbhag" in r.owner_reply_text


def test_pipeline_evon_path_and_translation(monkeypatch):
    monkeypatch.setattr(config, "EVON_BASE_URL", "http://evon.test")
    ticket_json = {"machine_type": "CNC lathe", "symptoms": ["spindle overheating"], "urgency": "high",
                   "skills_required": ["cnc"], "owner_reply": "Samajh gaye, spindle garam hai.",
                   "technician_brief": "CNC spindle overheating.", "caller_language": "hi-en"}
    replies = iter([json.dumps(ticket_json), "சிஎன்சி ஸ்பிண்டில் சூடாகிறது."])

    def fake_post(url, **kw):
        return FakeResp(body={"choices": [{"message": {"content": next(replies)}}]})

    monkeypatch.setattr(evon.requests, "post", fake_post)
    monkeypatch.setattr(pipeline.tts, "synthesize", lambda text, lang, voice: lang.encode())
    r = pipeline.run(None, ".wav", FACTORY, downtime.DowntimeInputs(),
                     transcript_override="CNC ka spindle garam ho raha hai", speak_replies=True)
    assert r.ticket.reasoner == "evon"
    assert r.match.technician["id"] == "T2"            # Tamil-speaking CNC specialist
    assert r.tech_brief_language == "ta-IN" and r.tech_brief_audio == b"ta-IN"


def test_pipeline_safety_overrides_llm(monkeypatch):
    monkeypatch.setattr(pipeline.tts, "synthesize", lambda *a, **k: b"WAV")
    r = pipeline.run(None, ".wav", FACTORY, downtime.DowntimeInputs(),
                     transcript_override="motor se dhuaan aa raha hai")
    assert r.danger == ["smoke"] and r.ticket.urgency == "critical"
    assert r.safety_alert_audio == b"WAV" and r.safety_alert_text


def test_pipeline_evon_down_falls_back(monkeypatch):
    monkeypatch.setattr(config, "EVON_BASE_URL", "http://evon.test")

    def boom(url, **kw):
        raise evon.requests.ConnectionError("offline")

    monkeypatch.setattr(evon.requests, "post", boom)
    r = pipeline.run(None, ".wav", FACTORY, downtime.DowntimeInputs(),
                     transcript_override="lathe mein awaaz aa rahi hai", speak_replies=False)
    assert r.ticket.reasoner == "fallback" and any("Evon unavailable" in w for w in r.warnings)


def test_wer():
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), "eval"))
    from run_eval import wer
    assert wer("spindle garam hai", "spindle garam hai") == 0
    assert round(wer("spindle garam hai", "spindal garam"), 2) == 0.67


# ---------- new features ----------
from core import actions, costs, db, escalation, firstaid, language, noise, sla  # noqa: E402
from reasoner import workflows  # noqa: E402


def test_language_resolution():
    assert language.resolve("CNC machine ka spindle garam ho raha hai") == "hi-en"
    assert language.resolve("The compressor is not building pressure") == "en-IN"
    assert language.resolve("மெஷின் ஓடவில்லை") == "ta-IN"
    assert language.resolve("मशीन बंद हो गई है", "hi-IN") == "hi-IN"
    assert language.resolve("मशीन बंद पडली आहे", "mr-IN") == "mr-IN"
    assert language.resolve("CNC का spindle garam हो रहा है motor bhi", "hi-IN") == "hi-en"


def test_eta_sentences_use_words():
    assert language.eta_sentence("hi-en", "Murugan", 2.2) == "Murugan ji lagbhag do ghante mein pahunchenge."
    assert "two hours" in language.eta_sentence("en-IN", "Murugan", 2)
    assert "2" in language.eta_sentence("ta-IN", "Murugan", 2)


def test_first_aid_is_safe():
    assert firstaid.checks(["oil or fluid leak"], [], False, "hi-en")[0].startswith("Leak ke neeche tray")
    assert firstaid.checks(["machine overheating"], [], True, "hi-en") == []          # never on danger
    evon_tips = ["Panel khol ke wire check kijiye", "Error code note kar lijiye"]
    assert firstaid.checks([], evon_tips, False, "hi-en") == ["Error code note kar lijiye"]


def test_escalation_rules():
    assert escalation.detect("kitni baar bolu, abhi tak koi nahi aaya").escalate
    assert not escalation.detect("spindle garam ho raha hai").escalate
    assert "repeat call" in escalation.detect("phir dekho", repeat_ticket={"id": 3, "status": "assigned"}).reason


def test_noise_meter_orders_clean_and_noisy():
    rng = np.random.default_rng(0)
    t = np.arange(16000 * 4) / 16000
    speech = (np.sin(2 * np.pi * 220 * t) * (np.sin(2 * np.pi * 0.5 * t) > 0) * 8000).astype(np.float32)
    clean = noise.estimate_samples(speech + rng.normal(0, 30, len(t)).astype(np.float32))
    noisy = noise.estimate_samples(speech + rng.normal(0, 3000, len(t)).astype(np.float32))
    assert clean.snr_db > noisy.snr_db and noisy.level == "high"


def test_sla_and_costs():
    due = sla.due_at("critical", created=0)
    assert due == 7200
    assert sla.describe(due, "assigned", now=8000)[1] == "overdue"
    assert sla.describe(due, "fixed", now=8000)[1] == "met"
    assert costs.call_cost(30, 300) == round(0.25 + 0.54, 2)


def test_ticket_lifecycle_and_qr_machine(monkeypatch):
    monkeypatch.setattr(pipeline.tts, "synthesize", lambda *a, **k: b"WAV")
    r = pipeline.run(None, ".wav", FACTORY, downtime.DowntimeInputs(), machine_id="M1",
                     transcript_override="machine mein awaaz aa rahi hai")
    row = db.get_ticket(r.ticket_id)
    assert row["machine_id"] == "M1" and row["machine_type"] == "cnc machine" and row["status"] == "assigned"
    db.set_status(r.ticket_id, "fixed", "done")
    assert db.get_ticket(r.ticket_id)["fixed_at"]
    assert [e["kind"] for e in db.events(r.ticket_id)][0] == "created"


def test_repeat_call_escalates_to_senior(monkeypatch):
    monkeypatch.setattr(pipeline.tts, "synthesize", lambda *a, **k: b"WAV")
    first = pipeline.run(None, ".wav", FACTORY, downtime.DowntimeInputs(), machine_id="M3",
                         transcript_override="hydraulic press mein oil leak hai")
    second = pipeline.run(None, ".wav", FACTORY, downtime.DowntimeInputs(), machine_id="M3",
                          transcript_override="hydraulic press mein oil leak hai")
    assert not first.escalation.escalate and second.escalation.escalate
    assert second.ticket.urgency in ("high", "critical") and second.repeat_count == 2


def test_tamil_caller_gets_tamil_reply(monkeypatch):
    seen = []
    monkeypatch.setattr(pipeline.tts, "synthesize", lambda text, lang, voice: seen.append(lang) or b"WAV")
    r = pipeline.run(None, ".wav", FACTORY, downtime.DowntimeInputs(), transcript_override="CNC மெஷின் சூடாகிறது",
                     detected_language="ta-IN")
    assert r.caller_language == "ta-IN" and r.owner_reply_text.startswith(language.ACK["ta-IN"])
    assert seen[0] == "ta-IN"


def test_technician_update_report_and_history(monkeypatch):
    monkeypatch.setattr(pipeline.tts, "synthesize", lambda *a, **k: b"WAV")
    r = pipeline.run(None, ".wav", FACTORY, downtime.DowntimeInputs(), machine_id="M2",
                     transcript_override="compressor mein pressure nahi ban raha")
    u = actions.technician_update(r.ticket_id, text="Main pahunch gaya hoon, valve chahiye")
    assert u.data["status"] == "on_site" and db.get_ticket(r.ticket_id)["status"] == "on_site"
    u = actions.technician_update(r.ticket_id, text="Machine theek ho gayi, chalu ho gaya")
    assert db.get_ticket(r.ticket_id)["status"] == "fixed"
    rep = actions.service_report(r.ticket_id, text="Relief valve badla. Pressure test kiya.")
    assert rep.data["work_done"] and "Service report" in actions.report_html(r.ticket_id)
    ans = actions.ask_history("F1", text="compressor kab kharab hua tha?", speak_reply=False)
    assert "compressor" in ans.data["answer"] and ans.data["tickets"] == [r.ticket_id]


def test_stream_headers_follow_docs(monkeypatch):
    from gnani import stt_stream
    h = stt_stream.headers("hi-IN,en-IN")
    assert stt_stream.stream_url() == "wss://api.vachana.ai/stt/v3/stream"
    assert h["x-api-key-id"] == "test-key" and h["language_code"] == "hi-IN,en-IN" and h["x-sample-rate"] == "16000"
    assert stt_stream.FRAME_BYTES == 1024


def test_streaming_against_fake_prisma_server(monkeypatch):
    """A local WebSocket server plays Prisma: checks frame size and commit, returns phrases."""
    import threading

    from websockets.sync.server import serve

    from gnani import stt_stream
    received = {"frames": 0, "bad": 0, "commit": False, "headers": {}}

    def handler(ws):
        received["headers"] = dict(ws.request.headers)
        ws.send(json.dumps({"type": "connected"}))
        for msg in ws:
            if isinstance(msg, bytes):
                received["frames"] += 1
                received["bad"] += len(msg) % 1024 != 0
                if received["frames"] == 20:
                    ws.send(json.dumps({"type": "transcript", "text": "spindle garam hai", "is_final": True}))
            elif json.loads(msg).get("type") == "commit":
                received["commit"] = True
                ws.send(json.dumps({"type": "transcript", "text": "production ruka hai", "is_final": True}))

    server = serve(handler, "127.0.0.1", 0)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    port = server.socket.getsockname()[1]
    monkeypatch.setattr(config, "GNANI_BASE_URL", f"http://127.0.0.1:{port}")
    monkeypatch.setattr(stt_stream, "FRAME_SECONDS", 0.001)
    pcm = b"\x01\x00" * 16000  # 1 s of audio
    texts = [m["text"] for m in stt_stream.stream_pcm(pcm, "hi-IN,en-IN", wait_after=1.0) if m["type"] == "transcript"]
    server.shutdown()
    assert texts == ["spindle garam hai", "production ruka hai"]
    assert received["commit"] and received["bad"] == 0 and received["frames"] >= 31
    assert received["headers"]["x-api-key-id"] == "test-key"


def test_follow_up_updates_same_ticket(monkeypatch):
    monkeypatch.setattr(pipeline.tts, "synthesize", lambda *a, **k: b"WAV")
    first = pipeline.run(None, ".wav", FACTORY, downtime.DowntimeInputs(), transcript_override="machine kharab hai")
    again = pipeline.run(None, ".wav", FACTORY, downtime.DowntimeInputs(),
                         transcript_override="machine kharab hai. lathe mein awaaz aa rahi hai",
                         update_ticket_id=first.ticket_id)
    assert again.ticket_id == first.ticket_id and not again.escalation.escalate
    assert db.get_ticket(first.ticket_id)["machine_type"] == "lathe"
    assert len(db.list_tickets()) == 1
