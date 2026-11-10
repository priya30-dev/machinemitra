"""MachineMitra — a voice repair line for small factories.
Run locally:  streamlit run app.py"""
import streamlit as st

import config
from core import budget, db, matching
from core.downtime import DowntimeInputs
from reasoner import evon
from ui import ask, board, evaluation, insights, machines, report
from ui.common import CSS
from ui.theme import hero

st.set_page_config(page_title="MachineMitra", page_icon=None, layout="wide")
st.markdown(CSS, unsafe_allow_html=True)

LANG_HINTS = {
    "Auto-detect (any of 10 languages)": "indic-auto",
    "Hinglish (Hindi + English)": "hi-IN,en-IN",
    "Tamil + English": "ta-IN,en-IN",
    "Marathi + Hindi": "mr-IN,hi-IN",
    "Bengali + English": "bn-IN,en-IN",
    "Telugu + English": "te-IN,en-IN",
    "Kannada + English": "kn-IN,en-IN",
    "Malayalam + English": "ml-IN,en-IN",
    "Gujarati + Hindi": "gu-IN,hi-IN",
    "Punjabi + Hindi": "pa-IN,hi-IN",
}


@st.cache_data(ttl=60, show_spinner=False)
def evon_status() -> bool:
    return evon.is_online()


directory = matching.load_directory()
qr_machine = st.query_params.get("machine")
qr_factory = (db.machine(qr_machine) or {}).get("factory_id") if qr_machine else None
factory_ids = [f["id"] for f in directory["factories"]]

with st.sidebar:
    st.header("Your factory")
    factory = st.selectbox("Location (demo)", directory["factories"], format_func=lambda f: f["name"],
                           index=factory_ids.index(qr_factory) if qr_factory in factory_ids else 0)
    st.caption("Downtime cost — rough numbers are fine")
    workers = st.number_input("Workers idle", 0, 500, 6)
    wage = st.number_input("Wage per worker per hour (₹)", 0, 2000, 90, step=10)
    output = st.number_input("Production lost per hour (₹)", 0, 500000, 3000, step=500)

    st.divider()
    st.header("Call settings")
    lang_label = st.selectbox("Caller's language", list(LANG_HINTS))
    telephony = st.toggle("Simulate phone-line audio (8 kHz)", value=False,
                          help="Downsamples recordings to phone quality before sending them to Prisma.")
    speak = st.toggle("Speak replies with Timbre", value=True)

    st.divider()
    st.header("Engines")
    st.markdown("**Prisma v3.0** speech to text · **Timbre v3.0** voice")
    if evon_status():
        st.success("Evon v3.3 online (self-hosted)")
    else:
        st.warning("Evon offline — tickets use the rule-based fallback and are labelled so.")
    left = config.MAX_RUNS_PER_SESSION - st.session_state.get("live_runs", 0)
    st.caption(f"Live runs left for you: **{max(left, 0)}** · today overall: "
               f"{budget.runs_today()}/{config.MAX_RUNS_PER_DAY}")

settings = {
    "factory": factory, "directory": directory, "telephony": telephony, "speak": speak,
    "languages": LANG_HINTS[lang_label], "downtime": DowntimeInputs(workers, wage, output),
}

hero()

tabs = st.tabs(["Report", "Technician board", "Machines & QR", "Insights", "Ask history",
                "Evaluation", "ℹHow it works"])
with tabs[0]:
    report.render(settings, qr_machine)
with tabs[1]:
    board.render(settings)
with tabs[2]:
    machines.render(settings)
with tabs[3]:
    insights.render(settings)
with tabs[4]:
    ask.render(settings)
with tabs[5]:
    evaluation.render(settings)
with tabs[6]:
    st.graphviz_chart("""
digraph {
  rankdir=LR; bgcolor="transparent"; edge [color="#5B6B85", penwidth=1.4];
  node [shape=box, style="rounded,filled", fillcolor="#0E1638", color="#5B8CFF", fontcolor="#E6EAF2", fontname="Helvetica"];
  call [label="Owner's call\\n(any of 10 languages)"];
  prisma [label="Gnani Prisma v3.0\\nspeech to text\\n(REST or realtime)"];
  noise [label="Noise meter\\n(SNR)", fillcolor="#1B2238", color="#A78BFA"];
  safety [label="Safety rules\\n(before any AI)", fillcolor="#3A1620", color="#FF4D5E"];
  evon [label="Gnani Evon v3.3\\nticket JSON"];
  esc [label="Escalation\\n+ SLA timer", fillcolor="#1B2238", color="#A78BFA"];
  match [label="Technician match\\n+ downtime cost", fillcolor="#1B2238", color="#A78BFA"];
  aid [label="First-aid\\nsafe checks", fillcolor="#1B2238", color="#A78BFA"];
  tr [label="Evon translation\\nfor technician"];
  timbre [label="Gnani Timbre v3.0\\nvoice replies"];
  db [label="SQLite tickets\\n+ timeline", shape=cylinder, fillcolor="#1B2238", color="#A78BFA"];
  call -> prisma -> safety -> evon -> esc -> match -> aid -> timbre;
  prisma -> noise; match -> tr -> timbre; timbre -> db;
}""")
    st.markdown("""
- **Gnani Prisma v3.0** transcribes the call — through the realtime WebSocket API (phrases appear as soon as they're
  recognised) or the REST API (long calls split into 28-second chunks). Factory words are passed as `keyterms`.
- **Safety rules** scan for sparks, smoke, fire, gas or shock *before* any AI runs and speak a warning instantly.
- **Gnani Evon v3.3** (self-hosted open weights) writes the ticket: symptoms, likely causes, urgency, skills, parts,
  safe first-aid checks and follow-up questions, in the caller's language. If it's offline, a rule-based fallback
  runs and is labelled.
- **Escalation** catches frustrated or repeat callers. **SLA timers** track arrival promises.
- **Evon** translates the technician's briefing into their language and powers voice updates, service reports and
  history questions. **Gnani Timbre v3.0** speaks every reply.

Technician names, factories and machines are fictional demo data.
""")
