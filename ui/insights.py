"""Tab 4 — owner insights from the ticket database."""
import time

import pandas as pd
import streamlit as st

from core import db, sla
from core.downtime import inr


def render(settings: dict):
    st.subheader("Owner insights")
    scope = st.radio("Show", ["This factory", "All factories"], horizontal=True)
    rows = db.list_tickets(factory_id=settings["factory"]["id"] if scope == "This factory" else None, limit=1000)
    if not rows:
        st.info("No tickets yet. Insights appear after a few calls.")
        return
    df = pd.DataFrame([{
        "id": r["id"], "machine": r["machine_type"], "machine_id": r["machine_id"], "urgency": r["urgency"],
        "status": r["status"], "loss": r["expected_loss"] or 0, "api_cost": r["api_cost"] or 0,
        "seconds": r["seconds_to_ticket"] or 0, "escalated": r["escalated"], "snr": r["snr_db"],
        "day": time.strftime("%Y-%m-%d", time.localtime(r["created"])),
        "sla_met": sla.describe(r["due_at"], r["status"])[1] in ("met", "ok", "soon"),
    } for r in rows])

    c = st.columns(5)
    c[0].metric("Breakdowns", len(df))
    c[1].metric("Downtime cost until arrival", inr(df["loss"].sum()))
    c[2].metric("Avg call → ticket", f"{df['seconds'].mean():.1f} s")
    c[3].metric("API cost, all calls", f"₹{df['api_cost'].sum():.2f}")
    c[4].metric("Within SLA", f"{100 * df['sla_met'].mean():.0f}%")

    a, b = st.columns(2)
    with a:
        st.markdown("**Breakdowns per machine**")
        st.bar_chart(df.groupby("machine").size().rename("tickets"), horizontal=True, color="#5B8CFF")
    with b:
        st.markdown("**Urgency mix**")
        st.bar_chart(df.groupby("urgency").size().reindex(["critical", "high", "medium", "low"]).fillna(0)
                     .rename("tickets"), color="#7DD3FC")
    st.markdown("**Breakdowns per day**")
    st.line_chart(df.groupby("day").size().rename("tickets"), color="#A78BFA")

    repeats = df.groupby("machine").size()
    repeats = repeats[repeats >= 2].sort_values(ascending=False)
    if len(repeats):
        st.markdown("**Repeat faults — candidates for preventive maintenance**")
        for machine, n in repeats.items():
            st.markdown(f"- **{machine}**: {n} breakdowns")
    st.caption(f"Escalated calls: {int(df['escalated'].sum())} · data from this app's ticket database.")
