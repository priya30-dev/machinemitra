"""Gnani Timbre text-to-speech (REST).

Endpoint and body follow https://docs.gnani.ai/api/TTS/tts-inference
  POST {base}/api/v1/tts/inference   JSON   header X-API-Key-ID
  text, model (timbre-v3.0 | timbre-v2.5), voice, language, speed (0.85-1.15), audio_config
Returns raw WAV bytes. timbre-v3.0 voices speak all 10 supported languages.
"""
import config
from gnani.errors import post_with_retry

# Languages Timbre accepts (docs). hi-en = Hinglish.
TTS_LANGUAGES = {"auto", "hi-IN", "en-IN", "hi-en", "ta-IN", "te-IN", "kn-IN",
                 "ml-IN", "mr-IN", "pa-IN", "bn-IN", "gu-IN"}
TIMBRE_V3_VOICES = ["Avinash", "Shivani", "Lakshmi", "Kalpana", "Shubham", "Prakash",
                    "Devansh", "Yashraj", "Chetana", "Vasudha", "Riyaa", "Tarika", "Harshad"]
MAX_CHARS = 600  # docs: overly long text returns 500, so keep replies short


def synthesize(text: str, language: str = "hi-en", voice: str | None = None,
               speed: float = 1.0) -> bytes:
    if not config.GNANI_API_KEY:
        raise RuntimeError("GNANI_API_KEY is not set. Add it to .env or Streamlit secrets.")
    if language not in TTS_LANGUAGES:
        language = "auto"
    body = {
        "text": text.strip()[:MAX_CHARS],
        "model": config.TTS_MODEL,
        "voice": voice or config.TTS_VOICE_OWNER,
        "language": language,
        "speed": max(0.85, min(1.15, speed)),
        "audio_config": {"sample_rate": 24000, "num_channels": 1, "sample_width": 2,
                         "encoding": "linear_pcm", "container": "wav"},
    }
    resp = post_with_retry(
        f"{config.GNANI_BASE_URL}/api/v1/tts/inference",
        headers={"Content-Type": "application/json", "X-API-Key-ID": config.GNANI_API_KEY},
        json=body, timeout=60,
    )
    return resp.content
