"""Tab 5 — ask your repair history by voice (Evon reads every past ticket)."""
import streamlit as st

from core import actions, db
from gnani.errors import GnaniError
from ui.common import can_go_live, note_live_run


def render(settings: dict):
    st.subheader("🗣️ Ask your repair history")
    st.markdown('Ask by voice, for example *"Pichhli baar compressor kab kharab hua tha?"* or '
                '*"Is mahine kaunsi machine sabse zyada band hui?"*. Evon reads all past tickets for this factory '
                "(it has a 128K-token context) and answers in your language.")
    machines = db.machines(settings["factory"]["id"])
    mid = st.selectbox("Only this machine (optional)", [None] + [m["id"] for m in machines],
                       format_func=lambda i: "All machines" if i is None else db.machine(i)["name"])
    q_audio = st.audio_input("Ask by voice")
    q_text = st.text_input("…or type the question")
    if st.button("Ask", type="primary"):
        try:
            if q_audio is not None:
                if not can_go_live():
                    return
                note_live_run()
                res = actions.ask_history(settings["factory"]["id"], audio=q_audio.getvalue(),
                                          languages=settings["languages"], machine_id=mid,
                                          speak_reply=settings["speak"])
            elif q_text.strip():
                res = actions.ask_history(settings["factory"]["id"], text=q_text, machine_id=mid,
                                          speak_reply=settings["speak"])
            else:
                st.warning("Record or type a question first.")
                return
        except GnaniError as e:
            st.error(e.friendly)
            return
        st.caption(f"Heard: “{res.heard}” · answered by {res.data['engine']}")
        st.markdown(f"> {res.data['answer']}")
        if res.audio:
            st.audio(res.audio, format="audio/wav", autoplay=True)
        if res.data.get("tickets"):
            st.caption("Based on tickets: " + ", ".join(f"#{i}" for i in res.data["tickets"]))
        for w in res.warnings:
            st.info(w)
