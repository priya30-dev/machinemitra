"""Audio helpers built on the ffmpeg command line (no pydub: it breaks on
Python 3.13). Prisma REST accepts at most 30 seconds per request, so longer
recordings are split into chunks."""
import json
import os
import subprocess
import tempfile

CHUNK_SECONDS = 28  # stay safely under Prisma's 30 s REST limit


def _run(cmd: list[str]) -> bytes:
    result = subprocess.run(cmd, capture_output=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg failed: {result.stderr.decode(errors='ignore')[-300:]}")
    return result.stdout


def duration_seconds(audio: bytes, suffix: str = ".wav") -> float:
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as f:
        f.write(audio)
        path = f.name
    try:
        out = _run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                    "-of", "json", path])
        return float(json.loads(out)["format"]["duration"])
    finally:
        os.unlink(path)


def to_wav_chunks(audio: bytes, suffix: str = ".wav", chunk_seconds: int = CHUNK_SECONDS,
                  telephony: bool = False) -> list[bytes]:
    """Convert any input to 16 kHz mono WAV and split into chunks.

    telephony=True first squeezes the audio to 8 kHz, like a real phone line,
    so you can test how Prisma handles call-quality audio."""
    with tempfile.TemporaryDirectory() as tmp:
        src = os.path.join(tmp, "in" + suffix)
        with open(src, "wb") as f:
            f.write(audio)
        filters = "aresample=8000,aresample=16000" if telephony else "aresample=16000"
        pattern = os.path.join(tmp, "chunk_%03d.wav")
        _run(["ffmpeg", "-y", "-v", "error", "-i", src, "-af", filters, "-ac", "1",
              "-f", "segment", "-segment_time", str(chunk_seconds), "-c:a", "pcm_s16le", pattern])
        chunks = []
        for name in sorted(os.listdir(tmp)):
            if name.startswith("chunk_"):
                with open(os.path.join(tmp, name), "rb") as f:
                    data = f.read()
                if len(data) > 3200:  # skip near-empty tail (<0.1 s)
                    chunks.append(data)
        return chunks
