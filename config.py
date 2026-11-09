"""Central settings. Values come from environment variables (.env locally,
Streamlit secrets when deployed). Never hard-code keys here."""
import os

from dotenv import load_dotenv

load_dotenv()


def _get(name: str, default: str = "") -> str:
    value = os.getenv(name)
    if value:
        return value
    # Streamlit Cloud exposes secrets through st.secrets; read lazily so the
    # rest of the code (tests, scripts) works without Streamlit running.
    try:
        import streamlit as st

        if name in st.secrets:
            return str(st.secrets[name])
    except Exception:
        pass
    return default


GNANI_API_KEY = _get("GNANI_API_KEY")
GNANI_BASE_URL = _get("GNANI_BASE_URL", "https://api.vachana.ai")

# Prisma (speech to text)
STT_MODEL = _get("STT_MODEL", "prisma-v3.0")
STT_LANGUAGES = _get("STT_LANGUAGES", "hi-IN,en-IN")  # Hinglish by default

# Timbre (text to speech). Every timbre-v3.0 voice speaks all 10 languages.
TTS_MODEL = _get("TTS_MODEL", "timbre-v3.0")
TTS_VOICE_OWNER = _get("TTS_VOICE_OWNER", "Shivani")
TTS_VOICE_TECH = _get("TTS_VOICE_TECH", "Avinash")

# Evon (self-hosted, OpenAI-compatible server such as llama.cpp's llama-server)
EVON_BASE_URL = _get("EVON_BASE_URL").rstrip("/")
EVON_API_KEY = _get("EVON_API_KEY")
EVON_MODEL = _get("EVON_MODEL", "evon")
EVON_TIMEOUT = float(_get("EVON_TIMEOUT", "90"))

# Credit protection for the public demo
MAX_RUNS_PER_SESSION = int(_get("MAX_RUNS_PER_SESSION", "5"))
MAX_RUNS_PER_DAY = int(_get("MAX_RUNS_PER_DAY", "400"))
MAX_AUDIO_SECONDS = int(_get("MAX_AUDIO_SECONDS", "60"))
DEMO_MODE = _get("DEMO_MODE", "false").lower() == "true"  # true = no live API calls

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
CACHE_DIR = _get("CACHE_DIR", os.path.join(os.path.dirname(__file__), ".cache"))
