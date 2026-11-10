# MachineMitra: solution pitch

**Voice-first breakdown response for small factories, built on Gnani AI**
[Live demo](https://machinemitra.streamlit.app) · [Source code](https://github.com/priya30-dev/machinemitra) · Team: Priya Singh, Mishita Joshi · Category: B2B Services

---

### Problem
When a machine fails in a small factory, **production stops and every hour costs thousands of rupees** in idle wages and lost output. Faults are reported by phone in Hinglish or a regional language, over machine noise. Technicians arrive without a diagnosis or the right parts, repeat visits are common, and nothing is recorded, so recurring failures go unnoticed.

### Solution
MachineMitra converts a spoken breakdown report into a managed repair in about **30 seconds**:

| Step | What happens | Gnani model |
|---|---|---|
| **Listen** | Transcribes noisy, code-mixed speech in 10 Indian languages plus Hinglish, in real time | Prisma v3.0 |
| **Protect** | Detects hazards (sparks, smoke, gas, shock) and issues a spoken power-off warning before any AI runs | Rules + Timbre |
| **Diagnose** | Ranked causes with confidence, urgency, parts and tools, safe checks for the owner, follow-up questions | Evon v3.3 |
| **Dispatch** | Nearest qualified technician, an urgency-based arrival deadline, escalation for repeat or frustrated callers | — |
| **Respond** | A voice confirmation in the owner's language, and a briefing in the technician's own language | Timbre v3.0 + Evon |
| **Track** | Status lifecycle, voice updates from technicians, service reports, QR-tagged machine history, insights | Prisma + Evon |

### Target users
Small and medium manufacturers (CNC and machine shops, foundries, plastics, packaging) and the **maintenance contractors** who serve many of them. These businesses rarely run maintenance software, but every owner has a phone and speaks their own language.

### Impact
- **Cost:** a full call costs about **₹1** in API usage, against **₹3,540 per hour** of downtime in our demo factory.
- **Speed:** about **30 seconds** from the end of the call to a dispatched technician with a diagnosis and parts list.
- **Safety:** hazard warnings are rule-based and never wait for a model.
- **Inclusion:** it works in the language owners actually speak, including on noisy, phone-quality audio.

### Technical highlights
- **Prisma** through both the realtime WebSocket and REST APIs, with domain keyterms and chunking for long calls.
- **Evon v3.3** self-hosted on a free T4 GPU (IQ4_XS, 97% GPU-resident) through Ollama, with thinking disabled and streamed responses. There's a labelled rule-based fallback when it's offline.
- **Timbre** voices for owner and technician across 10 languages plus Hinglish.
- **Production practices:** 32 automated tests in CI, credit controls, content-addressed caching, a per-step latency and engine trace, and an evaluation harness for quiet, noisy and 8 kHz audio.

### Why Gnani AI
The problem lives on noisy phone lines, in code-mixed Indian speech, which is exactly what Gnani's stack is built for. Prisma handles the input, Evon the reasoning, and Timbre closes the loop in the caller's language.

### Next steps
Telephony intake (a dial-in number), WhatsApp voice notes, multi-tenant accounts for maintenance contractors, and predictive maintenance from repair history.

<sub>Demo technicians, factories and machines are fictional sample data.</sub>
