"""Tab 2 — technician board: lifecycle, SLA timer, map, voice updates, service report."""
import time

import pandas as pd
import streamlit as st

from core import actions, db, language, sla
from gnani.errors import GnaniError
from ui.common import can_go_live, nice, note_live_run, pill, urgency_pill

NEXT = {"open": "assigned", "assigned": "on_the_way", "on_the_way": "on_site", "on_site": "fixed"}


def _ticket_card(row: dict, directory: dict, settings: dict):
    tech = next((t for t in directory["technicians"] if t["id"] == row["technician_id"]), None)
    fac = next((f for f in directory["factories"] if f["id"] == row["factory_id"]), None)
    m = db.machine(row["machine_id"]) if row["machine_id"] else None
    sla_label, sla_state = sla.describe(row["due_at"], row["status"])

    head = urgency_pill(row["urgency"]) + pill(db.STATUS_LABELS[row["status"]], "eng") + \
        pill(("⏱ " if sla_state != "met" else "✅ ") + sla_label, f"s-{sla_state}")
    if row["escalated"]:
        head += pill("ESCALATED", "esc")
    title = f"#{row['id']} · {nice(m['name'] if m else row['machine_type'])} · {fac['name'] if fac else ''}"
    with st.container(border=True):
        st.markdown(f"**{title}**")
        st.markdown(head, unsafe_allow_html=True)
        st.caption(f"Reported {time.strftime('%d %b %H:%M', time.localtime(row['created']))} · "
                   f"Technician: {tech['name'] if tech else 'unassigned'} · "
                   f"Caller language: {language.NAMES.get(row['language'], row['language'])}")
        with st.expander("Details, timeline and actions"):
            t = row.get("ticket") or {}
            if row["escalated"]:
                st.warning(f"Escalation: {row['escalation_reason']}")
            st.markdown(f"**Symptoms:** {', '.join(t.get('symptoms', [])) or '—'}  \n"
                        f"**Parts to carry:** {', '.join(t.get('parts_to_carry', [])) or '—'}")
            st.caption("Caller said: " + (row["transcript"] or "")[:300])
            if fac and tech:
                st.map(pd.DataFrame([{"lat": fac["lat"], "lon": fac["lon"], "size": 60, "color": "#E8590C"},
                                     {"lat": tech["lat"], "lon": tech["lon"], "size": 40, "color": "#4c4fd6"}]),
                       latitude="lat", longitude="lon", size="size", color="color", zoom=11, height=220)
                st.caption("🟠 factory · 🔵 technician (demo locations)")

            st.markdown("**Timeline**")
            for e in db.events(row["id"]):
                st.markdown(f"- `{time.strftime('%H:%M', time.localtime(e['ts']))}` {e['text']}")
                if e["audio"]:
                    st.audio(e["audio"], format="audio/wav")

            c1, c2 = st.columns(2)
            nxt = NEXT.get(row["status"])
            if nxt and c1.button(f"Mark: {db.STATUS_LABELS[nxt]}", key=f"next_{row['id']}"):
                db.set_status(row["id"], nxt, note="updated from board")
                st.rerun()

            if row["status"] != "fixed":
                st.markdown("**🎙️ Technician voice update**")
                st.caption('e.g. "Nikal gaya hoon", "Pahunch gaya, bearing kharab hai", "Machine theek ho gayi"')
                upd = st.audio_input("Record update", key=f"upd_{row['id']}")
                if upd is not None and st.button("Apply update", key=f"apply_{row['id']}") and can_go_live():
                    note_live_run()
                    try:
                        res = actions.technician_update(row["id"], audio=upd.getvalue(),
                                                        languages=settings["languages"])
                    except GnaniError as e:
                        st.error(e.friendly)
                    else:
                        st.success(f"Heard: “{res.heard}” → status **{db.STATUS_LABELS[res.data['status']]}** "
                                   f"({res.data.get('engine')}). Owner is told: {res.data.get('owner_message')}")
                        st.rerun()
            else:
                st.markdown("**🧾 Service report**")
                if row.get("report"):
                    st.download_button("Download service report", actions.report_html(row["id"]),
                                       file_name=f"service_report_{row['id']}.html", mime="text/html",
                                       key=f"dl_{row['id']}")
                    st.caption(f"Engine: {row['report'].get('engine')} · open it in a browser and print to PDF.")
                st.caption("Technician speaks a 20-second summary: what was wrong, what was replaced.")
                summ = st.audio_input("Record summary", key=f"rep_{row['id']}")
                if summ is not None and st.button("Create report", key=f"mk_{row['id']}") and can_go_live():
                    note_live_run()
                    try:
                        actions.service_report(row["id"], audio=summ.getvalue(), languages=settings["languages"])
                    except GnaniError as e:
                        st.error(e.friendly)
                    else:
                        st.rerun()


def render(settings: dict):
    directory = settings["directory"]
    st.subheader("🧰 Technician board")
    f1, f2, f3 = st.columns(3)
    status = f1.selectbox("Status", ["All open", "All"] + db.STATUSES,
                          format_func=lambda s: db.STATUS_LABELS.get(s, s))
    urgency = f2.selectbox("Urgency", ["All", "critical", "high", "medium", "low"])
    only_overdue = f3.toggle("Only overdue", value=False)

    rows = db.list_tickets(status=status if status in db.STATUSES else None)
    if status == "All open":
        rows = [r for r in rows if r["status"] != "fixed"]
    if urgency != "All":
        rows = [r for r in rows if r["urgency"] == urgency]
    if only_overdue:
        rows = [r for r in rows if sla.describe(r["due_at"], r["status"])[1] == "overdue"]
    order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    rows.sort(key=lambda r: (not r["escalated"], order.get(r["urgency"], 2), r["due_at"]))

    counts = {s: 0 for s in db.STATUSES}
    for r in db.list_tickets():
        counts[r["status"]] += 1
    cols = st.columns(len(db.STATUSES))
    for c, s in zip(cols, db.STATUSES):
        c.metric(db.STATUS_LABELS[s], counts[s])

    if not rows:
        st.info("No tickets match. Report a breakdown or run a sample call first.")
    for row in rows[:30]:
        _ticket_card(row, directory, settings)
