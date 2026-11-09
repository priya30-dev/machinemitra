"""Shared UI helpers and the credit guard."""
import streamlit as st

import config
from core import budget

from ui.theme import CSS  # noqa: E402,F401  (theme lives in ui/theme.py)


def nice(name: str) -> str:
    return (name or "")[:1].upper() + (name or "")[1:]


def pill(text: str, cls: str) -> str:
    return f'<span class="mm-pill {cls}">{text}</span>'


def urgency_pill(u: str) -> str:
    return pill(u.upper(), f"u-{u}")


def can_go_live() -> bool:
    """Per-visitor and daily caps that protect the team's Gnani credits."""
    if config.DEMO_MODE:
        return True
    ss = st.session_state
    if ss.get("live_runs", 0) >= config.MAX_RUNS_PER_SESSION:
        st.error("You've used this demo's live runs. Try a sample call, or clone the repo and use your own key.")
        return False
    if not budget.can_run_today():
        st.error("Today's demo limit is reached (it protects our API credits). Sample calls still work.")
        return False
    return True


def note_live_run() -> None:
    st.session_state["live_runs"] = st.session_state.get("live_runs", 0) + 1
    budget.note_run()


def audio_suffix(uploaded) -> str:
    name = getattr(uploaded, "name", "") or ""
    return "." + name.rsplit(".", 1)[-1] if "." in name else ".wav"
