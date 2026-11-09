"""Protects the team's 5,000 Gnani credits on the public demo link:
  - result cache keyed by audio hash, so replays cost nothing
  - a daily cap on live runs across all visitors
(The per-visitor limit lives in Streamlit session state, in app.py.)"""
import hashlib
import json
import os
import pickle
import threading
import time

import config

_LOCK = threading.Lock()


def _dir() -> str:
    os.makedirs(config.CACHE_DIR, exist_ok=True)
    return config.CACHE_DIR


def cache_key(*parts) -> str:
    h = hashlib.sha256()
    for p in parts:
        h.update(p if isinstance(p, bytes) else str(p).encode())
    return h.hexdigest()[:32]


def cache_get(key: str):
    path = os.path.join(_dir(), f"{key}.pkl")
    if os.path.exists(path):
        with open(path, "rb") as f:
            return pickle.load(f)
    return None


def cache_put(key: str, value) -> None:
    with open(os.path.join(_dir(), f"{key}.pkl"), "wb") as f:
        pickle.dump(value, f)


def _counter_path() -> str:
    return os.path.join(_dir(), "daily_runs.json")


def runs_today() -> int:
    try:
        with open(_counter_path()) as f:
            data = json.load(f)
        return data["count"] if data.get("day") == time.strftime("%Y-%m-%d") else 0
    except (FileNotFoundError, json.JSONDecodeError, KeyError):
        return 0


def can_run_today() -> bool:
    return runs_today() < config.MAX_RUNS_PER_DAY


def note_run() -> None:
    with _LOCK:
        count = runs_today() + 1
        with open(_counter_path(), "w") as f:
            json.dump({"day": time.strftime("%Y-%m-%d"), "count": count}, f)
