"""Noise meter: estimates how noisy a call is, as a signal-to-noise ratio (SNR).

Method: decode to 16 kHz mono, split into 30 ms frames, take the loud frames
(90th percentile energy) as speech and the quiet frames (10th percentile) as
background noise. It's a quick estimate, not a lab measurement, but it's
consistent, so it lets us compare Prisma's accuracy across quiet and noisy calls."""
import math
import subprocess
from dataclasses import dataclass

import numpy as np

FRAME = 480  # 30 ms at 16 kHz


@dataclass
class NoiseReading:
    snr_db: float
    level: str   # low | moderate | high
    label: str


def decode_pcm(audio: bytes, telephony: bool = False) -> np.ndarray:
    filters = "aresample=8000,aresample=16000" if telephony else "aresample=16000"
    out = subprocess.run(["ffmpeg", "-v", "error", "-i", "pipe:0", "-af", filters, "-ac", "1",
                          "-f", "s16le", "pipe:1"], input=audio, capture_output=True, check=True).stdout
    return np.frombuffer(out, dtype=np.int16).astype(np.float32)


def classify(snr_db: float) -> NoiseReading:
    if snr_db >= 25:
        return NoiseReading(round(snr_db, 1), "low", f"Quiet call · {snr_db:.0f} dB SNR")
    if snr_db >= 15:
        return NoiseReading(round(snr_db, 1), "moderate", f"Some background noise · {snr_db:.0f} dB SNR")
    return NoiseReading(round(snr_db, 1), "high", f"Very noisy call · {snr_db:.0f} dB SNR")


def estimate_samples(samples: np.ndarray) -> NoiseReading | None:
    n = len(samples) // FRAME
    if n < 10:
        return None
    frames = samples[: n * FRAME].reshape(n, FRAME)
    rms = np.sqrt(np.mean(frames ** 2, axis=1)) + 1e-6
    speech, noise = np.percentile(rms, 90), np.percentile(rms, 10)
    snr = 20 * math.log10(speech / noise) if noise > 1 else 60.0
    return classify(min(snr, 60.0))


def estimate(audio: bytes, telephony: bool = False) -> NoiseReading | None:
    try:
        return estimate_samples(decode_pcm(audio, telephony))
    except Exception:
        return None
