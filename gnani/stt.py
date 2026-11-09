"""Gnani Prisma speech-to-text (REST).

Endpoint and fields follow https://docs.gnani.ai/api/STT/speech-to-text.md
  POST {base}/stt/v3   multipart/form-data   header X-API-Key-ID
  audio_file (<=30 s), model=prisma-v3.0, language_code (1-4 codes or indic-auto),
  format (verbatim|transcribe|codemix|transliterate), keyterms, topic, previous_text
"""
import json
from dataclasses import dataclass, field

import config
from gnani.audio import to_wav_chunks
from gnani.errors import post_with_retry

# Shop-floor words Prisma should favour (keyterms supports up to 200 phrases).
FACTORY_KEYTERMS = [
    "CNC", "lathe", "spindle", "bearing", "motor", "gearbox", "hydraulic", "pump",
    "compressor", "conveyor", "belt", "coolant", "VFD", "PLC", "panel", "MCB",
    "contactor", "injection moulding", "boiler", "welding", "chuck", "oil leak",
    "overheating", "vibration", "short circuit", "pressure", "RPM",
]
TOPIC = ("A small factory owner calling a repair helpline to report a machine "
         "breakdown, often in Hinglish, with shop-floor noise.")


@dataclass
class Transcript:
    text: str
    language: str | None = None
    chunks: int = 0
    audio_seconds: float = 0.0
    raw: list[dict] = field(default_factory=list)


def transcribe(audio: bytes, suffix: str = ".wav", languages: str | None = None,
               output_format: str = "codemix", telephony: bool = False) -> Transcript:
    """Transcribe audio of any length by sending <=28 s chunks one at a time.

    Chunks go sequentially because some accounts allow only one active request
    (docs: 429 RATE_LIMITED). Each chunk gets the previous text as context."""
    if not config.GNANI_API_KEY:
        raise RuntimeError("GNANI_API_KEY is not set. Add it to .env or Streamlit secrets.")

    chunks = to_wav_chunks(audio, suffix=suffix, telephony=telephony)
    url = f"{config.GNANI_BASE_URL}/stt/v3"
    headers = {"X-API-Key-ID": config.GNANI_API_KEY}
    texts, raws, lang = [], [], None

    for i, chunk in enumerate(chunks):
        data = {
            "model": config.STT_MODEL,
            "language_code": languages or config.STT_LANGUAGES,
            "format": output_format,
            "keyterms": json.dumps(FACTORY_KEYTERMS, ensure_ascii=False),
            "topic": TOPIC,
        }
        if texts:
            data["previous_text"] = " ".join(texts)[-600:]
        resp = post_with_retry(
            url, headers=headers, data=data, timeout=60,
            files={"audio_file": (f"chunk_{i}.wav", chunk, "audio/wav")},
        )
        body = resp.json()
        raws.append(body)
        if body.get("transcript"):
            texts.append(body["transcript"].strip())
        lang = lang or body.get("detected_language_code")

    return Transcript(text=" ".join(texts).strip(), language=lang, chunks=len(chunks),
                      audio_seconds=round(sum(max(len(c) - 44, 0) for c in chunks) / 32000, 1), raw=raws)
