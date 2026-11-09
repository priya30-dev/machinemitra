"""API cost per call, so the app can show 'this call cost ₹0.9 vs ₹3,540/hr downtime'.

TTS rate is MEASURED from the team's Gnani usage page (Nov 5, 2026):
199 characters = 0.36 credits, 109 characters = 0.20 credits -> ~0.0018 credits/char.
STT rate is an ESTIMATE until measured (set STT_CREDITS_PER_MIN once you have a
real STT row from the usage page). 1 credit = ₹1 on the dashboard."""
import config

TTS_CREDITS_PER_CHAR = float(config._get("TTS_CREDITS_PER_CHAR", "0.0018"))
STT_CREDITS_PER_MIN = float(config._get("STT_CREDITS_PER_MIN", "0.5"))
STT_IS_MEASURED = config._get("STT_CREDITS_PER_MIN", "") != ""


def call_cost(stt_seconds: float, tts_chars: int) -> float:
    return round(stt_seconds / 60 * STT_CREDITS_PER_MIN + tts_chars * TTS_CREDITS_PER_CHAR, 2)
