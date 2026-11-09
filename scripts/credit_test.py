"""Measure what one Prisma call and one Timbre call cost in credits.

Usage:
  1. Note the credits shown on app.gnani.ai (e.g. "5k / 5k Left").
  2. python scripts/credit_test.py samples/your_20s_clip.wav
  3. Refresh the dashboard and compare. Divide by the numbers printed below.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gnani import stt, tts  # noqa: E402

if len(sys.argv) < 2:
    sys.exit("Usage: python scripts/credit_test.py <audio file>")

path = sys.argv[1]
with open(path, "rb") as f:
    audio = f.read()

tr = stt.transcribe(audio, suffix=os.path.splitext(path)[1] or ".wav")
print(f"Prisma: {tr.audio_seconds}s of audio in {tr.chunks} request(s)")
print("Transcript:", tr.text)

sentence = "Aapka ticket ban gaya hai. Technician do ghante mein pahunchenge."
wav = tts.synthesize(sentence, "hi-en")
os.makedirs("samples", exist_ok=True)
with open("samples/credit_test_tts.wav", "wb") as f:
    f.write(wav)
print(f"Timbre: {len(sentence)} characters -> samples/credit_test_tts.wav")
print("\nNow check the credit drop on the dashboard and tell your teammate the numbers.")
