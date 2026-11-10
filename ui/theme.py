"""Visual theme: deep-space 'astral' look — blue/violet nebula, glass panels,
3D tilt on hover, and a header where stars fly in and assemble into a 3D gear
beside a typed owner/MachineMitra conversation.

Everything is drawn with a tiny hand-written 3D projection on <canvas>, so it
needs no external JavaScript library and always loads."""
import streamlit.components.v1 as components

FONTS = ("https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;600;700"
         "&family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap")

CSS = f"""
<style>
@import url('{FONTS}');
:root {{
  --bg: #030617; --panel: rgba(255,255,255,.035); --panel-2: rgba(255,255,255,.06);
  --line: rgba(255,255,255,.09); --text: #E6EAF2; --muted: #8A93A6;
  --saffron: #5B8CFF; --amber: #A5C8FF; --cyan: #7DD3FC; --violet: #A78BFA;
  --red: #FF4D5E; --green: #2EE59D;
}}
html, body, [class*="css"], .stMarkdown, p, li, label {{ font-family: 'Inter', sans-serif; }}
h1, h2, h3, h4, h5 {{ font-family: 'Space Grotesk', sans-serif !important; letter-spacing: -.01em; }}
code, pre {{ font-family: 'JetBrains Mono', monospace !important; }}

/* background: deep navy with drifting colour glows and a faint grid */
[data-testid="stAppViewContainer"] {{
  background:
    radial-gradient(900px 520px at 10% -10%, rgba(59,91,255,.22), transparent 60%),
    radial-gradient(800px 520px at 95% 0%, rgba(125,211,252,.12), transparent 60%),
    radial-gradient(800px 620px at 50% 115%, rgba(167,139,250,.16), transparent 60%),
    var(--bg);
}}
[data-testid="stAppViewContainer"]::before {{
  content: ""; position: fixed; inset: 0; pointer-events: none; z-index: 0;
  background-image: linear-gradient(rgba(255,255,255,.025) 1px, transparent 1px),
                    linear-gradient(90deg, rgba(255,255,255,.025) 1px, transparent 1px);
  background-size: 44px 44px;
  mask-image: radial-gradient(ellipse at 50% 0%, black 20%, transparent 75%);
}}
[data-testid="stHeader"] {{ background: transparent; }}
.block-container {{ padding-top: 1rem; max-width: 1280px; position: relative; z-index: 1; }}

/* sidebar: frosted glass */
[data-testid="stSidebar"] {{
  background: linear-gradient(180deg, rgba(10,16,44,.92), rgba(3,6,23,.96));
  border-right: 1px solid var(--line); backdrop-filter: blur(14px);
}}
[data-testid="stSidebar"] h2 {{ font-size: 1.05rem; color: var(--amber); }}

/* tabs as glowing pills */
.stTabs [data-baseweb="tab-list"] {{
  gap: 6px; background: var(--panel); border: 1px solid var(--line); padding: 6px;
  border-radius: 14px; backdrop-filter: blur(10px); overflow-x: auto;
}}
.stTabs button[data-baseweb="tab"] {{
  border-radius: 10px !important; padding: 8px 16px !important; height: auto; color: var(--muted);
  transition: all .2s ease;
}}
.stTabs button[data-baseweb="tab"]:hover {{ color: var(--text); background: var(--panel-2); }}
.stTabs [role="tab"] {{ border-radius: 10px !important; flex-shrink: 0; white-space: nowrap; }}
.stTabs [aria-selected="true"] {{
  color: #fff !important;
  background: linear-gradient(135deg, rgba(91,140,255,.95), rgba(167,139,250,.85)) !important;
  box-shadow: 0 6px 26px -6px rgba(91,140,255,.75);
}}
.stTabs [data-baseweb="tab-highlight"], .stTabs [data-baseweb="tab-border"] {{ display: none; }}

/* glass cards with 3D lift on hover */
[data-testid="stVerticalBlockBorderWrapper"]:has(> div > [data-testid="stVerticalBlock"]),
[data-testid="stMetric"], [data-testid="stExpander"], .mm-card {{
  background: linear-gradient(145deg, rgba(255,255,255,.055), rgba(255,255,255,.015));
  border: 1px solid var(--line) !important; border-radius: 16px !important;
  box-shadow: 0 1px 0 rgba(255,255,255,.06) inset, 0 18px 40px -22px rgba(0,0,0,.8);
  backdrop-filter: blur(12px);
  transition: transform .25s ease, box-shadow .25s ease, border-color .25s ease;
}}
[data-testid="stMetric"] {{ padding: 14px 16px; transform-style: preserve-3d; }}
[data-testid="stMetric"]:hover, .mm-card:hover {{
  transform: perspective(700px) rotateX(5deg) rotateY(-5deg) translateY(-3px);
  border-color: rgba(125,211,252,.45) !important;
  box-shadow: 0 1px 0 rgba(255,255,255,.08) inset, 0 26px 50px -20px rgba(91,140,255,.45);
}}
[data-testid="stMetricLabel"] p {{ color: var(--muted); text-transform: uppercase; font-size: .72rem;
  letter-spacing: .08em; }}
[data-testid="stMetricValue"] {{
  font-size: clamp(1.25rem, 2.1vw, 1.7rem) !important; white-space: normal !important; font-family: 'Space Grotesk', sans-serif; font-weight: 700;
  background: linear-gradient(90deg, #fff, var(--amber)); -webkit-background-clip: text;
  background-clip: text; color: transparent;
}}
.mm-card {{ padding: 16px 18px; margin-bottom: 10px; }}

/* buttons */
.stButton > button, .stDownloadButton > button, .stLinkButton > a {{
  border-radius: 12px; border: 1px solid var(--line); background: var(--panel-2);
  color: var(--text); transition: all .2s ease; font-weight: 600;
}}
.stButton > button:hover, .stDownloadButton > button:hover, .stLinkButton > a:hover {{
  border-color: var(--cyan); color: #fff; box-shadow: 0 0 0 1px var(--cyan), 0 8px 26px -8px rgba(34,211,238,.6);
  transform: translateY(-1px);
}}
.stButton > button[kind="primary"] {{
  background: linear-gradient(135deg, #5B8CFF, #A78BFA); border: none; color: #fff;
  box-shadow: 0 10px 30px -10px rgba(91,140,255,.9);
}}
.stButton > button[kind="primary"]:hover {{ box-shadow: 0 14px 40px -8px rgba(125,211,252,.9); color: #fff; }}

/* inputs */
[data-baseweb="select"] > div, [data-baseweb="input"] > div, .stTextArea textarea, .stNumberInput input {{
  background: rgba(255,255,255,.04) !important; border-color: var(--line) !important; border-radius: 10px !important;
}}
[data-testid="stAudioInput"], [data-testid="stFileUploaderDropzone"] {{
  background: rgba(34,211,238,.05) !important; border: 1px dashed rgba(34,211,238,.35) !important;
  border-radius: 14px !important;
}}
audio {{ color-scheme: dark; border-radius: 999px; width: 100%; }}
.stAppDeployButton, [data-testid="stAppDeployButton"] {{ display: none !important; }}

/* alerts */
[data-testid="stAlert"] {{ border-radius: 14px; backdrop-filter: blur(8px); }}

/* pills */
.mm-pill {{ display:inline-block; padding:3px 11px; border-radius:999px; font-size:.75rem; font-weight:600;
  margin:0 6px 6px 0; border:1px solid transparent; letter-spacing:.02em; }}
.u-critical {{ background:rgba(255,77,94,.16); color:#FF8A96; border-color:rgba(255,77,94,.45);
  box-shadow:0 0 18px -4px rgba(255,77,94,.7); animation: pulse 1.6s ease-in-out infinite; }}
.u-high {{ background:rgba(255,122,26,.15); color:#FFB06E; border-color:rgba(255,122,26,.4); }}
.u-medium {{ background:rgba(255,181,71,.12); color:#FFD38A; border-color:rgba(255,181,71,.35); }}
.u-low {{ background:rgba(46,229,157,.12); color:#7DF2C3; border-color:rgba(46,229,157,.35); }}
.s-ok {{ background:rgba(34,211,238,.12); color:#7DE8F7; border-color:rgba(34,211,238,.35); }}
.s-soon {{ background:rgba(255,181,71,.12); color:#FFD38A; border-color:rgba(255,181,71,.35); }}
.s-overdue {{ background:rgba(255,77,94,.16); color:#FF8A96; border-color:rgba(255,77,94,.45); }}
.s-met {{ background:rgba(46,229,157,.12); color:#7DF2C3; border-color:rgba(46,229,157,.35); }}
.eng {{ background:rgba(139,92,246,.14); color:#C4B1FF; border-color:rgba(139,92,246,.35); }}
.esc {{ background:linear-gradient(135deg,#FF4D5E,#FF7A1A); color:#fff; }}
.n-low {{ background:rgba(46,229,157,.12); color:#7DF2C3; border-color:rgba(46,229,157,.35); }}
.n-moderate {{ background:rgba(255,181,71,.12); color:#FFD38A; border-color:rgba(255,181,71,.35); }}
.n-high {{ background:rgba(255,77,94,.16); color:#FF8A96; border-color:rgba(255,77,94,.45); }}
@keyframes pulse {{ 50% {{ box-shadow: 0 0 28px 0 rgba(255,77,94,.9); }} }}

/* live transcript box */
.live-box {{ border: 1px solid rgba(34,211,238,.35); padding: 12px 16px; border-radius: 14px; min-height: 52px;
  background: linear-gradient(90deg, rgba(34,211,238,.10), rgba(139,92,246,.08));
  box-shadow: 0 0 30px -12px rgba(34,211,238,.7); font-family: 'JetBrains Mono', monospace; }}

/* section headings get a neon underline */
.block-container h3 {{ position: relative; padding-bottom: 8px; margin-bottom: 10px; }}
.block-container h3::after {{ content: ""; position: absolute; left: 0; bottom: 0; width: 46px; height: 3px;
  border-radius: 3px; background: linear-gradient(90deg, var(--saffron), var(--cyan)); }}
hr {{ border-color: var(--line) !important; }}
</style>
"""

HERO = """
<!doctype html><html><head><meta charset="utf-8">
<link href="__FONTS__" rel="stylesheet">
<style>
  * { box-sizing: border-box; margin: 0; }
  body { background: transparent; color: #E6EAF2; font-family: Inter, sans-serif; overflow: hidden; }
  .hero { position: relative; height: 380px; cursor: crosshair; border-radius: 24px; overflow: hidden; background: #030617;
    border: 1px solid rgba(165,200,255,.14); box-shadow: 0 40px 80px -40px rgba(30,60,200,.6); }
  canvas { position: absolute; inset: 0; width: 100%; height: 100%; }
  .copy { position: relative; z-index: 2; height: 100%; display: flex; flex-direction: column; justify-content: center;
    gap: 14px; padding: 0 40px; max-width: 640px; }
  .tag { align-self: flex-start; display: inline-flex; gap: 8px; align-items: center; font-size: 12px; color: #A5C8FF;
    background: rgba(91,140,255,.12); border: 1px solid rgba(125,170,255,.35); padding: 5px 12px; border-radius: 999px;
    letter-spacing: .08em; text-transform: uppercase; font-weight: 600; backdrop-filter: blur(6px); }
  .dot { width: 7px; height: 7px; border-radius: 50%; background: #7DD3FC; box-shadow: 0 0 10px #7DD3FC; animation: blink 1.4s infinite; }
  h1 { font-family: 'Space Grotesk', sans-serif; font-size: 58px; line-height: 1; letter-spacing: -.035em;
    background: linear-gradient(95deg, #FFFFFF 20%, #A5C8FF 55%, #A78BFA 90%); -webkit-background-clip: text;
    background-clip: text; color: transparent; text-shadow: 0 0 40px rgba(91,140,255,.25); }
  .chat { display: flex; flex-direction: column; gap: 10px; max-width: 520px; min-height: 132px; }
  .bubble { padding: 12px 16px; border-radius: 16px; font-size: 14.5px; line-height: 1.5; backdrop-filter: blur(10px); }
  .you { align-self: flex-start; background: rgba(255,255,255,.06); border: 1px solid rgba(255,255,255,.12);
    font-family: 'JetBrains Mono', monospace; font-size: 13.5px; color: #E6EAF2; }
  .you .who, .bot .who { display: block; font-family: Inter, sans-serif; font-size: 11px; letter-spacing: .1em;
    text-transform: uppercase; margin-bottom: 4px; }
  .you .who { color: #8FA3C8; } .bot .who { color: #7DD3FC; }
  .bot { align-self: flex-end; background: linear-gradient(135deg, rgba(91,140,255,.22), rgba(167,139,250,.18));
    border: 1px solid rgba(125,170,255,.35); opacity: 0; transform: translateY(6px); transition: all .5s ease; }
  .bot.show { opacity: 1; transform: none; }
  .caret { display: inline-block; width: 8px; height: 15px; background: #7DD3FC; vertical-align: -2px; margin-left: 2px;
    animation: blink 1s steps(1) infinite; }
  .chips { display: flex; gap: 8px; flex-wrap: wrap; }
  .chip { font-family: 'JetBrains Mono', monospace; font-size: 12px; padding: 5px 10px; border-radius: 9px;
    background: rgba(3,6,23,.55); border: 1px solid rgba(165,200,255,.18); color: #C9D6F2; }
  .chip b { color: #7DD3FC; font-weight: 500; }
  @keyframes blink { 50% { opacity: .3; } }
  @media (max-width: 760px) { .copy { padding: 0 20px; } h1 { font-size: 40px; } .chat { min-height: 150px; } }
</style></head><body>
<div class="hero">
  <canvas id="c"></canvas>
  <div class="copy">
    <span class="tag"><span class="dot"></span>Voice repair line · Gnani AI</span>
    <h1>MachineMitra</h1>
    <div class="chat">
      <div class="bubble you"><span class="who" id="who">Factory owner · Hinglish</span><span id="typed"></span><span class="caret"></span></div>
      <div class="bubble bot" id="bot"><span class="who">MachineMitra</span><span id="reply"></span></div>
    </div>
    <div class="chips">
      <span class="chip"><b>Prisma</b> listens</span><span class="chip"><b>Evon</b> reasons</span><span class="chip"><b>Timbre</b> speaks</span>
    </div>
  </div>
</div>
<script>
// ---------- typed conversation ----------
const convo = [
  ["Factory owner · Hinglish", "CNC machine ka spindle bahut garam ho raha hai, production ruka hua hai…",
   "Ticket ban gaya. CNC expert Murugan ji lagbhag ek ghante mein pahunchenge."],
  ["Factory owner · safety", "Panel se chingari nikal rahi hai, jalne ki smell aa rahi hai!",
   "Main power turant band kijiye aur sabko machine se door rakhiye. Technician bhej rahe hain."],
  ["Factory owner · Tamil", "CNC மெஷின் ரொம்ப சூடாகுது, உற்பத்தி நின்றுவிட்டது.",
   "உங்கள் புகார் கிடைத்தது, நாங்கள் டெக்னீஷியனை அனுப்புகிறோம்."],
];
const typed = document.getElementById('typed'), reply = document.getElementById('reply'),
      bot = document.getElementById('bot'), who = document.getElementById('who');
const sleep = ms => new Promise(r => setTimeout(r, ms));
const scene = { talking: false, pulses: [] };   // shared with the 3D scene below
(async function loop() {
  for (let k = 0; ; k = (k + 1) % convo.length) {
    const [w, q, a] = convo[k];
    who.textContent = w; typed.textContent = ''; bot.classList.remove('show'); reply.textContent = '';
    scene.talking = true;
    for (const ch of Array.from(q)) { typed.textContent += ch; await sleep(32 + Math.random() * 40); }
    scene.talking = false;
    await sleep(700); reply.textContent = a; bot.classList.add('show');
    scene.pulses.push({ at: performance.now(), red: w.includes('safety') });
    await sleep(4200);
  }
})();

// ---------- nebula + star field that assembles into a 3D gear ----------
const cv = document.getElementById('c'), ctx = cv.getContext('2d');
let W = 0, H = 0, DPR = 1;
const neb = document.createElement('canvas'), nctx = neb.getContext('2d');
function size() {
  DPR = Math.min(window.devicePixelRatio || 1, 2); W = cv.clientWidth; H = cv.clientHeight;
  cv.width = W * DPR; cv.height = H * DPR; ctx.setTransform(DPR, 0, 0, DPR, 0, 0);
  const NW = W * 1.8, NH = H * 1.8, ox = W * .4, oy = H * .4;   // oversized so edges never show
  neb.width = NW; neb.height = NH;
  const blobs = [[.72, .45, .55, '40,70,220'], [.85, .2, .35, '120,90,240'], [.55, .8, .4, '30,140,230'],
                 [.95, .7, .3, '90,60,200'], [.25, .3, .45, '20,40,140']];
  nctx.clearRect(0, 0, NW, NH);
  for (const [x, y, r, c] of blobs) {
    const bx = ox + x * W, by = oy + y * H;
    const g = nctx.createRadialGradient(bx, by, 0, bx, by, r * W);
    g.addColorStop(0, `rgba(${c},.42)`); g.addColorStop(.5, `rgba(${c},.12)`); g.addColorStop(1, `rgba(${c},0)`);
    nctx.fillStyle = g; nctx.fillRect(0, 0, NW, NH);
  }
}
size(); addEventListener('resize', size);

// target points: gear outline (two layers), hub ring and spokes
function gearPoints() {
  const pts = [], teeth = 12, rIn = 92, rOut = 116;
  const outline = [];
  for (let i = 0; i < teeth * 4; i++) {
    const a = i / (teeth * 4) * Math.PI * 2, r = (i % 4 < 2) ? rOut : rIn;
    outline.push([Math.cos(a) * r, Math.sin(a) * r]);
  }
  for (const z of [-16, 16])
    for (let i = 0; i < outline.length; i++) {
      const [x1, y1] = outline[i], [x2, y2] = outline[(i + 1) % outline.length];
      for (let t = 0; t < 1; t += 0.12) pts.push([x1 + (x2 - x1) * t, y1 + (y2 - y1) * t, z]);
    }
  for (let i = 0; i < 70; i++) { const a = i / 70 * Math.PI * 2; pts.push([Math.cos(a) * 34, Math.sin(a) * 34, 0]); }
  for (let k = 0; k < 6; k++) { const a = k / 6 * Math.PI * 2;
    for (let r = 38; r < 88; r += 5) pts.push([Math.cos(a) * r, Math.sin(a) * r, 0]); }
  return pts;
}
const targets = gearPoints();
const stars = targets.map(t => ({ t, x: (Math.random() - .5) * 2400, y: (Math.random() - .5) * 1600,
  z: 600 + Math.random() * 1800, tw: Math.random() * 6.28, hue: Math.random() < .25 ? 1 : 0,
  ang: Math.atan2(t[1], t[0]) }));
let burstAt = -1e9;                                       // click the header: stars scatter, then reassemble
document.querySelector('.hero').addEventListener('click', () => { burstAt = performance.now(); });
const comets = Array.from({length: 3}, () => ({ next: performance.now() + 1500 + Math.random() * 6000, life: 0 }));
let talk = 0;
const dust = Array.from({length: 260}, () => ({ x: (Math.random() - .5) * 2000, y: (Math.random() - .5) * 1200,
  z: Math.random() * 2000 }));
let mx = 0, my = 0;
addEventListener('mousemove', e => { mx = e.clientX / innerWidth - .5; my = e.clientY / innerHeight - .5; });

const start = performance.now();
function frame(now) {
  const t = (now - start) / 1000;
  ctx.clearRect(0, 0, W, H);
  ctx.save(); ctx.globalAlpha = .9; ctx.translate(W * .5, H * .5); ctx.rotate(Math.sin(t * .05) * .06);
  ctx.drawImage(neb, -neb.width / 2, -neb.height / 2); ctx.restore();

  // star flight: background dust drifting towards the camera
  const fx = W * .5, fy = H * .5;
  for (const d of dust) {
    d.z -= 2.2; if (d.z < 1) { d.z = 2000; d.x = (Math.random() - .5) * 2000; d.y = (Math.random() - .5) * 1200; }
    const f = 300 / d.z, x = fx + d.x * f, y = fy + d.y * f;
    if (x < 0 || x > W || y < 0 || y > H) continue;
    ctx.fillStyle = `rgba(200,220,255,${Math.min(.8, f * .6)})`;
    ctx.fillRect(x, y, Math.max(.6, f * 1.2), Math.max(.6, f * 1.2));
  }

  // comets: occasional shooting stars across the nebula
  for (const c of comets) {
    if (now > c.next && c.life <= 0) {
      c.x = W * (.35 + Math.random() * .65); c.y = -20; c.vx = -(5 + Math.random() * 4); c.vy = 3 + Math.random() * 2.5;
      c.life = 1; c.next = now + 4000 + Math.random() * 7000;
    }
    if (c.life > 0) {
      c.x += c.vx; c.y += c.vy; c.life -= .012;
      const g = ctx.createLinearGradient(c.x, c.y, c.x - c.vx * 14, c.y - c.vy * 14);
      g.addColorStop(0, `rgba(220,235,255,${c.life})`); g.addColorStop(1, 'rgba(120,160,255,0)');
      ctx.strokeStyle = g; ctx.lineWidth = 1.6;
      ctx.beginPath(); ctx.moveTo(c.x, c.y); ctx.lineTo(c.x - c.vx * 14, c.y - c.vy * 14); ctx.stroke();
      ctx.fillStyle = `rgba(255,255,255,${c.life})`; ctx.beginPath(); ctx.arc(c.x, c.y, 1.8, 0, 6.283); ctx.fill();
    }
  }

  // gear: stars fly in over ~3.5 s, then the gear rotates in 3D
  const k = Math.min(1, t / 3.5), ease = 1 - Math.pow(1 - k, 3);
  const bt = (now - burstAt) / 1000, burst = bt >= 0 && bt < 2.2 ? Math.sin(Math.PI * bt / 2.2) : 0;
  const form = ease * (1 - burst * .9);
  const cx = W > 760 ? W * .74 : W * .5, cy = H * .5, scale = Math.min(1.25, H / 300);
  talk += ((scene.talking ? 1 : 0) - talk) * .06;
  const spin = t * .35 + burst * 2, ax = -0.45 + my * .5, ay = 0.35 + mx * .8 + Math.sin(t * .3) * .15;
  const mobile = W <= 760;

  // latest reply pulse (red for a safety call)
  let red = 0;
  scene.pulses = scene.pulses.filter(p => now - p.at < 2200);
  for (const p of scene.pulses) if (p.red) red = Math.max(red, 1 - (now - p.at) / 2200);

  // energy core glow, breathing with the voice
  const coreR = (190 + 40 * talk) * scale;
  const glow = ctx.createRadialGradient(cx, cy, 0, cx, cy, coreR);
  glow.addColorStop(0, red ? `rgba(255,80,90,${.35 * red + .1})` : `rgba(91,140,255,${(.25 + .15 * talk) * form})`);
  glow.addColorStop(1, 'rgba(91,140,255,0)');
  ctx.fillStyle = glow; ctx.fillRect(0, 0, W, H);

  function project(x, y, z) {
    let c = Math.cos(ax), si = Math.sin(ax); [y, z] = [y * c - z * si, y * si + z * c];
    c = Math.cos(ay); si = Math.sin(ay); [x, z] = [x * c + z * si, -x * si + z * c];
    const f = 500 / (500 + z * scale); return [cx + x * scale * f, cy + y * scale * f, f];
  }

  ctx.globalCompositeOperation = 'lighter';
  ctx.globalAlpha = mobile ? .45 : 1;

  // voice ring: a waveform orbiting the gear, loud while the owner is talking
  ctx.beginPath();
  for (let i = 0; i <= 220; i++) {
    const a = i / 220 * Math.PI * 2;
    const amp = (2 + 12 * talk) * (Math.sin(a * 9 + t * 5) * .6 + Math.sin(a * 23 - t * 7) * .4);
    const r = 132 + amp;
    const [px, py] = project(Math.cos(a) * r, Math.sin(a) * r * .32, Math.sin(a) * r * .95 - 10);
    i ? ctx.lineTo(px, py) : ctx.moveTo(px, py);
  }
  ctx.strokeStyle = `rgba(125,211,252,${(.35 + .45 * talk) * form})`; ctx.lineWidth = 1.4; ctx.stroke();

  // shockwave rings when MachineMitra replies
  for (const p of scene.pulses) {
    const q = (now - p.at) / 2200, r = (40 + q * 260) * scale;
    ctx.strokeStyle = p.red ? `rgba(255,90,100,${(1 - q) * .8})` : `rgba(165,200,255,${(1 - q) * .7})`;
    ctx.lineWidth = 2.5 * (1 - q) + .5;
    ctx.beginPath(); ctx.ellipse(cx, cy, r, r * .55, -0.2, 0, 6.283); ctx.stroke();
  }

  // radar sweep: a beam circling the gear lights up the stars it passes
  const sweep = (t * 1.1) % (Math.PI * 2);
  for (const s of stars) {
    let [x, y, z] = s.t;
    let c = Math.cos(spin), si = Math.sin(spin); [x, y] = [x * c - y * si, x * si + y * c];
    const [gx, gy, gf] = project(x, y, z);
    const sx = s.x, sy = s.y, sz = s.z, f0 = 500 / (500 + sz), fx0 = W * .5 + sx * f0, fy0 = H * .5 + sy * f0;
    const px = fx0 + (gx - fx0) * form, py = fy0 + (gy - fy0) * form, f = f0 + (gf - f0) * form;
    let d = Math.abs(((s.ang + spin) % (Math.PI * 2) + Math.PI * 2) % (Math.PI * 2) - sweep);
    d = Math.min(d, Math.PI * 2 - d);
    const beam = Math.exp(-d * d * 18) * form;
    const tw = .65 + .35 * Math.sin(t * 3 + s.tw);
    const a = Math.min(1, Math.max(.15, f * f) * tw + beam * .9);
    if (red > 0) ctx.fillStyle = `rgba(255,${120 + 100 * (1 - red) | 0},${130 + 120 * (1 - red) | 0},${a})`;
    else ctx.fillStyle = s.hue ? `rgba(196,170,255,${a})` : `rgba(${150 + 105 * beam | 0},${200 + 55 * beam | 0},255,${a})`;
    const r = Math.max(.7, 1.6 * f) * (1 + beam * 1.2);
    ctx.beginPath(); ctx.arc(px, py, r, 0, 6.283); ctx.fill();
  }

  // bright core sparkle at the hub
  const sp = ctx.createRadialGradient(cx, cy, 0, cx, cy, 26 * scale * (1 + .4 * talk));
  sp.addColorStop(0, `rgba(255,255,255,${.55 * form})`); sp.addColorStop(1, 'rgba(165,200,255,0)');
  ctx.fillStyle = sp; ctx.beginPath(); ctx.arc(cx, cy, 30 * scale * (1 + .4 * talk), 0, 6.283); ctx.fill();

  ctx.globalCompositeOperation = 'source-over'; ctx.globalAlpha = 1;
  requestAnimationFrame(frame);
}
requestAnimationFrame(frame);
</script></body></html>
""".replace("__FONTS__", FONTS)


def hero():
    components.html(HERO, height=390)

