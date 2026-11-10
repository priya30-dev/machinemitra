"""Tab 3 — machines and printable QR stickers."""
import time

import streamlit as st

import config
from core import db, qr


def render(settings: dict):
    st.subheader("Machines & QR stickers")
    st.markdown("Print a sticker for each machine. Scanning it opens MachineMitra with the machine already chosen, "
                "so the owner only has to describe the problem — and every repair builds that machine's history.")
    base = st.text_input("App link to put in the QR codes", value=config._get("APP_URL", "http://localhost:8501"),
                         help="After deploying, paste your public Streamlit link here (or set APP_URL in secrets).")
    machines = db.machines(settings["factory"]["id"])
    cols = st.columns(3)
    for i, m in enumerate(machines):
        url = qr.machine_url(base, m["id"])
        png = qr.sticker_png(url, m["name"], f"{m['model']} · since {m['installed']}")
        history = db.recent_for_machine(m["factory_id"], m["id"], m["machine_type"], days=365)
        with cols[i % 3].container(border=True):
            st.image(png, width="stretch")
            st.markdown(f"**{m['name']}**  \n{m['model']} · installed {m['installed']}")
            st.caption(f"{len(history)} repair(s) in the last year"
                       + (f" · last on {time.strftime('%d %b', time.localtime(history[0]['created']))}"
                          if history else ""))
            st.download_button("Download sticker", png, file_name=f"machinemitra_{m['id']}.png",
                               mime="image/png", key=f"qr_{m['id']}")
            st.link_button("Open as if scanned", url)
    st.caption("Machines are demo data.")
