"""Gnani Prisma real-time transcription over WebSocket.

Protocol per https://docs.gnani.ai/api/STT/stt-websocket.md
  URL     wss://api.vachana.ai/stt/v3/stream
  Headers x-api-key-id, language_code, model, format, x-sample-rate (config is headers, no query params)
  Audio   raw PCM s16le mono, frames of exactly 1024 bytes, sent at real-time cadence (32 ms at 16 kHz)
  End     {"type": "commit"} closes the open utterance
  Server  connected, speech_start, processing, transcript (final per segment), error

Prisma sends one final transcript per spoken phrase, so phrases appear on
screen as soon as each one is finished."""
import json
import threading
import time
from collections.abc import Iterator

from websockets.sync.client import connect

import config
from gnani.stt import FACTORY_KEYTERMS, TOPIC

FRAME_BYTES = 1024
FRAME_SECONDS = 0.032


def stream_url() -> str:
    return config.GNANI_BASE_URL.replace("https://", "wss://").replace("http://", "ws://") + "/stt/v3/stream"


def headers(languages: str, output_format: str = "codemix") -> dict:
    return {
        "x-api-key-id": config.GNANI_API_KEY,
        "language_code": languages,
        "model": config.STT_MODEL,
        "format": output_format,
        "x-sample-rate": "16000",
        "keyterms": json.dumps(FACTORY_KEYTERMS),
        "topic": TOPIC,
    }


def stream_pcm(pcm: bytes, languages: str, output_format: str = "codemix",
               wait_after: float = 4.0) -> Iterator[dict]:
    """Send 16 kHz PCM through Prisma's realtime API; yield server messages as they arrive."""
    if not config.GNANI_API_KEY:
        raise RuntimeError("GNANI_API_KEY is not set.")
    with connect(stream_url(), additional_headers=headers(languages, output_format),
                 open_timeout=15, max_size=2 ** 20) as ws:
        done = threading.Event()

        def sender():
            try:
                for i in range(0, len(pcm), FRAME_BYTES):
                    frame = pcm[i:i + FRAME_BYTES].ljust(FRAME_BYTES, b"\x00")
                    ws.send(frame)
                    time.sleep(FRAME_SECONDS)
                ws.send(b"\x00" * FRAME_BYTES * 30)  # ~1 s of silence closes the last phrase
                ws.send(json.dumps({"type": "commit"}))
            except Exception:
                pass
            finally:
                done.set()

        threading.Thread(target=sender, daemon=True).start()
        deadline = None
        while True:
            if done.is_set() and deadline is None:
                deadline = time.time() + wait_after
            if deadline and time.time() > deadline:
                break
            try:
                raw = ws.recv(timeout=0.5)
            except TimeoutError:
                continue
            except Exception:
                break
            if isinstance(raw, bytes):
                continue
            msg = json.loads(raw)
            yield msg
            if msg.get("type") == "transcript" and deadline:
                deadline = time.time() + 1.5  # more phrases may still be arriving
