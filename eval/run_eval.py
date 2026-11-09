"""Evaluate MachineMitra on your own recordings: clean vs noisy vs phone-line.

Put recordings in eval/audio/ and describe them in eval/cases.csv:
  id,file,condition,reference,machine,urgency
  c1,c1_quiet.wav,quiet,"CNC machine ka spindle garam ho raha hai",CNC,high
  c1n,c1_shop.wav,noisy,"CNC machine ka spindle garam ho raha hai",CNC,high

Then:  python eval/run_eval.py            (add --phone to also test 8 kHz audio)
Writes eval/results.csv and prints word error rate (WER) and ticket accuracy
per condition — numbers you can put in the README, the submission and your resume.
Each recording costs Prisma credits once; results are cached.

Transcripts are requested in Prisma's "transliterate" style (all Latin letters) so
they can be compared word-for-word with Roman-script references.
"""
import argparse
import csv
import os
import re
import sys
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from core import pipeline  # noqa: E402
from core.downtime import DowntimeInputs  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
FACTORY = {"id": "EVAL", "name": "Evaluation", "lat": 27.2046, "lon": 78.0350}


def normalize(text: str) -> list[str]:
    text = re.sub(r"[^\w\s]", " ", text.lower())
    return text.split()


def wer(reference: str, hypothesis: str) -> float:
    """Word error rate = word-level edit distance / reference length."""
    r, h = normalize(reference), normalize(hypothesis)
    if not r:
        return 0.0 if not h else 1.0
    prev = list(range(len(h) + 1))
    for i, rw in enumerate(r, 1):
        cur = [i] + [0] * len(h)
        for j, hw in enumerate(h, 1):
            cur[j] = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (rw != hw))
        prev = cur
    return prev[-1] / len(r)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cases", default=os.path.join(HERE, "cases.csv"))
    ap.add_argument("--phone", action="store_true", help="also run each file as 8 kHz phone audio")
    args = ap.parse_args()

    with open(args.cases, encoding="utf-8") as f:
        cases = list(csv.DictReader(f))
    runs = [(c, False) for c in cases] + ([(c, True) for c in cases] if args.phone else [])

    rows = []
    for case, phone in runs:
        path = os.path.join(HERE, "audio", case["file"])
        with open(path, "rb") as f:
            audio = f.read()
        res = pipeline.run(audio, os.path.splitext(path)[1], FACTORY, DowntimeInputs(),
                           telephony=phone, speak_replies=False, stt_format="transliterate", save=False)
        t = res.ticket
        condition = case["condition"] + ("+phone" if phone else "")
        rows.append({
            "id": case["id"], "condition": condition,
            "wer": round(wer(case["reference"], res.transcript), 3),
            "machine_ok": int(bool(t) and case["machine"].lower() in t.machine_type.lower()),
            "urgency_ok": int(bool(t) and t.urgency == case["urgency"].lower()),
            "reasoner": t.reasoner if t else "none",
            "snr_db": res.noise.snr_db if res.noise else "",
            "transcript": res.transcript,
        })
        print(f'{case["id"]:>6} {condition:<14} WER={rows[-1]["wer"]:.2f}  '
              f'machine={rows[-1]["machine_ok"]} urgency={rows[-1]["urgency_ok"]}')

    out = os.path.join(HERE, "results.csv")
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)

    groups = defaultdict(list)
    for r in rows:
        groups[r["condition"]].append(r)
    print("\nSummary")
    print(f'{"condition":<14} {"n":>3} {"avg WER":>8} {"machine":>8} {"urgency":>8}')
    for cond, rs in groups.items():
        n = len(rs)
        print(f'{cond:<14} {n:>3} {sum(r["wer"] for r in rs)/n:>8.2f} '
              f'{sum(r["machine_ok"] for r in rs)/n:>8.0%} {sum(r["urgency_ok"] for r in rs)/n:>8.0%}')
    print(f"\nSaved {out}")


if __name__ == "__main__":
    main()
