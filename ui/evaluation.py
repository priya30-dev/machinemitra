"""Tab 6 — evaluation: how well does it work on quiet, noisy and phone-line audio?
Shows real results from eval/results.csv only; never placeholder numbers."""
import os

import pandas as pd
import streamlit as st

from core import db

RESULTS = os.path.join(os.path.dirname(os.path.dirname(__file__)), "eval", "results.csv")


def render(settings: dict):
    st.subheader("Evaluation")
    st.markdown("We record the same complaints in a quiet room, on a noisy shop floor, and squeezed to 8 kHz "
                "phone quality, then measure **word error rate** (lower is better) and whether the ticket got the "
                "machine and urgency right.")
    if not os.path.exists(RESULTS):
        st.info("No results yet. Record test calls into `eval/audio/`, list them in `eval/cases.csv`, then run "
                "`python eval/run_eval.py --phone`. Results appear here automatically.")
    else:
        df = pd.read_csv(RESULTS)
        summary = df.groupby("condition").agg(calls=("id", "count"), avg_wer=("wer", "mean"),
                                              machine_ok=("machine_ok", "mean"), urgency_ok=("urgency_ok", "mean"))
        c = st.columns(len(summary))
        for col, (cond, s) in zip(c, summary.iterrows()):
            col.metric(cond, f"{(1 - s.avg_wer) * 100:.0f}% words right", f"{int(s.calls)} calls",
                       delta_color="off")
        a, b = st.columns(2)
        with a:
            st.markdown("**Word error rate by condition**")
            st.bar_chart(summary["avg_wer"], color="#5B8CFF")
        with b:
            if "snr_db" in df and df["snr_db"].notna().any():
                st.markdown("**Word error rate vs noise (SNR dB)**")
                st.scatter_chart(df.dropna(subset=["snr_db"]), x="snr_db", y="wer", color="condition")
        st.markdown("**Ticket accuracy**")
        st.dataframe((summary[["machine_ok", "urgency_ok"]] * 100).round(0).astype(int).astype(str) + "%")
        with st.expander("All results"):
            st.dataframe(df, width="stretch")

    rows = db.list_tickets(limit=1000)
    live = [r for r in rows if r["snr_db"] is not None]
    if live:
        st.markdown("**Live calls in this app: noise level vs time to ticket**")
        st.scatter_chart(pd.DataFrame([{"snr_db": r["snr_db"], "seconds_to_ticket": r["seconds_to_ticket"]}
                                       for r in live]), x="snr_db", y="seconds_to_ticket", color="#7DD3FC")
