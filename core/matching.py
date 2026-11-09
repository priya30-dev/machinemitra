"""Pick the best available technician: skill fit first, then distance, then rating.
Uses the clearly labelled demo data in data/technicians.json."""
import json
import math
import os
from dataclasses import dataclass

import config

AVG_SPEED_KMPH = 20.0   # city traffic
PREP_HOURS = 0.5        # time to leave with parts


@dataclass
class Match:
    technician: dict
    distance_km: float
    eta_hours: float
    skill_overlap: list[str]
    score: float


def load_directory(path: str | None = None) -> dict:
    with open(path or os.path.join(config.DATA_DIR, "technicians.json"), encoding="utf-8") as f:
        return json.load(f)


def haversine_km(lat1, lon1, lat2, lon2) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def rank(skills_needed: list[str], factory: dict, technicians: list[dict]) -> list[Match]:
    results = []
    needed = set(skills_needed or ["mechanical"])
    for t in technicians:
        if not t.get("available"):
            continue
        overlap = sorted(needed & set(t["skills"]))
        km = haversine_km(factory["lat"], factory["lon"], t["lat"], t["lon"]) * 1.3  # road factor
        eta = PREP_HOURS + km / AVG_SPEED_KMPH
        # skill fit dominates; each km costs a little; rating breaks ties
        score = 10 * len(overlap) / len(needed) - 0.3 * km + t.get("rating", 4.0)
        results.append(Match(t, round(km, 1), round(eta, 1), overlap, round(score, 2)))
    return sorted(results, key=lambda m: m.score, reverse=True)
