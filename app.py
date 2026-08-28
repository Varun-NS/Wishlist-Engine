"""
app.py
------
Wishlist Discovery Engine - executive interface.

Design system
  Surface   Apple-style frosted glass panels: 72-80% white over a soft gradient
            backdrop, 30px backdrop blur, 180% saturation, 22px radius. Opacity is
            deliberately high - Apple's own materials are near-opaque, and that is
            what keeps text legible on glass.
  Palette   Myntra light - rose #FF3F6C accent, ink #1C1E2E, muted #5C6076
            (every text colour clears 4.5:1 on the panel surface)
  Type      Outfit (headings) + DM Sans (body) on a 17px base, 1.7 line-height
  Icons     Material Symbols via Streamlit's `:material/...:` syntax + inline SVG.
            No emoji used as an icon.
  Charts    Single-hue magnitude bars with direct value labels; a validated 3-hue
            categorical set (#2563A8 / #0F8A6E / #B26B00) reserved for platform identity.

Structure
  Every section of every tab lives inside its own titled glass panel, so the page
  reads as a stack of discrete, self-describing parts rather than a continuous wall.

Navigation (5 top-level tabs, no nested tab layer)
  1. Overview          - headline, key numbers, motives, blockers, ranked matrix.
  2. Deep dives        - 4 strategic pillars behind one pill selector.
  3. AI copilot        - ask any question across the corpus.
  4. Voice of customer - verbatim evidence with filters and workarounds.
  5. How it works      - live extractor playground + methodology.
"""

import html
import math
import os
import re
import sys
import uuid
from contextlib import contextmanager

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "scripts"))
from taxonomy import BUCKETS, bucket_label, is_addressable

st.set_page_config(
    page_title="Wishlist Discovery Engine",
    page_icon="🛍️",
    layout="wide",
    # "auto" keeps the filter rail open on desktop but collapsed on phones,
    # where an expanded sidebar would sit on top of the content.
    initial_sidebar_state="auto",
)

# ------------------------------------------------------------------
# Design tokens (kept in sync with the CSS custom properties below)
# ------------------------------------------------------------------
BRAND = "#FF3F6C"       # Myntra rose - accents, CTAs
BRAND_INK = "#D92B58"   # accessible rose for data marks and small text
INK = "#1C1E2E"         # headings
BODY = "#33364A"        # body copy
MUTED = "#5C6076"       # captions, axis labels (5.9:1 on the panel surface)
LINE = "#E3E4EC"        # borders, gridlines

# Categorical hues for platform identity. Validated (light surface, all-pairs):
# CVD delta-E 9.9, normal-vision delta-E 17.0, contrast >= 3:1.
PLATFORM_COLORS = {"iOS": "#2563A8", "Android": "#0F8A6E", "YouTube": "#B26B00"}

# The store each platform key actually refers to, named the way the store is.
PLATFORM_NAMES = {"iOS": "App Store", "Android": "Google Play", "YouTube": "YouTube"}

CHART_FONT = "DM Sans, -apple-system, BlinkMacSystemFont, sans-serif"

st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:opsz,wght@9..40,400;9..40,500;9..40,600;9..40,700&family=Outfit:wght@500;600;700&display=swap');

:root {
    --brand: #FF3F6C;
    --brand-ink: #D92B58;
    --brand-soft: rgba(255, 63, 108, .09);
    --brand-line: rgba(255, 63, 108, .26);
    --ink: #1C1E2E;
    --body: #33364A;
    --muted: #5C6076;
    --line: #E3E4EC;
    --line-soft: rgba(28, 30, 46, .07);

    /* Apple-style material: high opacity + heavy blur = legible glass */
    --glass: rgba(255, 255, 255, .74);
    --glass-strong: rgba(255, 255, 255, .86);
    --glass-blur: saturate(180%) blur(30px);
    --glass-ring: 0 0 0 1px rgba(28, 30, 46, .06);
    --glass-edge: inset 0 1px 0 rgba(255, 255, 255, .85);
    --glass-shadow: 0 10px 34px -12px rgba(28, 30, 46, .18);

    --radius-xl: 22px;
    --radius-lg: 16px;
    --radius-md: 11px;
    --radius-sm: 7px;
    --ease: 220ms cubic-bezier(.32, .72, 0, 1);
}

/* ---------- Base typography: 17px base for comfortable reading ---------- */
html { font-size: 17px; }

html, body, .stMarkdown, p, li, label, input, textarea, button, div[data-baseweb] {
    font-family: 'DM Sans', -apple-system, BlinkMacSystemFont, sans-serif !important;
    -webkit-font-smoothing: antialiased;
}
.stMarkdown p, .stMarkdown li { color: var(--body); line-height: 1.7; font-size: 1rem; }
.stMarkdown li { margin-bottom: .35rem; }

h1, h2, h3, h4, h5, h6 {
    font-family: 'Outfit', -apple-system, sans-serif !important;
    color: var(--ink) !important;
    letter-spacing: -0.018em;
}

/* Never let the body font override Streamlit's icon font */
[data-testid*="Icon"], [data-testid="stExpanderToggleIcon"],
[class*="material-symbols"], [class*="material-icons"], span[data-testid="stIconMaterial"] {
    font-family: 'Material Symbols Rounded', 'Material Icons', sans-serif !important;
}

/* ---------- Canvas: a soft gradient field for the glass to refract ---------- */
.stApp {
    background-color: #EDEEF3;
    background-image:
        radial-gradient(58rem 40rem at 8% -10%, rgba(255, 63, 108, .16), transparent 62%),
        radial-gradient(52rem 38rem at 96% 2%,  rgba(96, 130, 255, .14), transparent 64%),
        radial-gradient(46rem 34rem at 52% 108%, rgba(255, 156, 92, .13), transparent 62%);
    background-attachment: fixed;
    background-repeat: no-repeat;
}
.main .block-container {
    padding-top: 2.25rem;
    padding-bottom: 5rem;
    max-width: 1200px;
}

/* ---------- THE GLASS PANEL ----------
   Every st.container(key="p_...") becomes a discrete frosted section.       */
[class*="st-key-p_"] {
    background: var(--glass);
    -webkit-backdrop-filter: var(--glass-blur);
    backdrop-filter: var(--glass-blur);
    border-radius: var(--radius-xl);
    padding: 1.6rem 1.75rem !important;
    margin-bottom: 1.35rem;
    box-shadow: var(--glass-ring), var(--glass-edge), var(--glass-shadow);
}
/* Panels sitting inside a column fill its height so a side-by-side row stays even.
   Streamlit nests them as stColumn > stVerticalBlock > stLayoutWrapper > panel. */
[data-testid="stColumn"] > [data-testid="stVerticalBlock"] { height: 100%; }
[data-testid="stColumn"] [data-testid="stLayoutWrapper"]:has(> [class*="st-key-p_"]) { height: 100%; }
[data-testid="stColumn"] [class*="st-key-p_"] { height: 100%; margin-bottom: 0; }

/* Panel header: icon chip + title + one line saying what the section is */
.metric-callout {
  background: linear-gradient(90deg, rgba(255,63,108,.09), rgba(255,63,108,.02));
  border-left: 3px solid var(--brand); border-radius: 10px;
  padding: .7rem 1rem; margin: 0 0 1.1rem;
  font-size: .95rem; line-height: 1.55; color: var(--ink);
}
.metric-callout span {
  display: block; font-size: .72rem; font-weight: 700; letter-spacing: .08em;
  text-transform: uppercase; color: var(--brand-ink); margin-bottom: .18rem;
}
.panel-head {
    display: flex; align-items: flex-start; gap: .8rem;
    padding-bottom: 1.05rem; margin-bottom: 1.15rem;
    border-bottom: 1px solid var(--line-soft);
}
.panel-head.bare { border-bottom: none; padding-bottom: 0; margin-bottom: 1.1rem; }
.panel-icon {
    width: 34px; height: 34px; flex-shrink: 0;
    display: grid; place-items: center;
    border-radius: 10px;
    background: var(--brand-soft);
    color: var(--brand-ink);
    box-shadow: inset 0 0 0 1px var(--brand-line);
}
.panel-title {
    font-family: 'Outfit', sans-serif;
    font-size: 1.2rem; font-weight: 600; color: var(--ink);
    line-height: 1.3; letter-spacing: -.015em;
}
.panel-desc { font-size: .93rem; color: var(--muted); margin-top: .2rem; line-height: 1.55; }

/* ---------- Header ---------- */
.app-header {
    display: flex; align-items: center; justify-content: space-between;
    gap: 1.5rem; flex-wrap: wrap;
    margin-bottom: 1.5rem;
}
.app-header .brand { display: flex; align-items: center; gap: 1rem; }
.app-header .brand-mark {
    width: 50px; height: 50px; flex-shrink: 0;
    display: grid; place-items: center;
    border-radius: 15px;
    background: var(--glass-strong);
    -webkit-backdrop-filter: var(--glass-blur);
    backdrop-filter: var(--glass-blur);
    color: var(--brand-ink);
    box-shadow: var(--glass-ring), var(--glass-edge), 0 6px 18px -8px rgba(28,30,46,.25);
}
.app-header h1 { font-size: 1.75rem; font-weight: 700; margin: 0; line-height: 1.15; }
.app-header .sub { font-size: .97rem; color: var(--muted); margin-top: .25rem; }
.source-strip { display: flex; align-items: center; gap: .5rem; flex-wrap: wrap; }
.source-chip {
    display: inline-flex; align-items: center; gap: .45rem;
    padding: .4rem .8rem; border-radius: 999px;
    background: var(--glass-strong);
    -webkit-backdrop-filter: var(--glass-blur);
    backdrop-filter: var(--glass-blur);
    box-shadow: var(--glass-ring), var(--glass-edge);
    color: var(--body); font-weight: 500; font-size: .87rem;
}
.source-chip .dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }

/* Store marks. Given their own breathing room so each keeps its clear space,
   and never recoloured - they carry brand colour, the UI does not tint them. */
.plat-logo { flex-shrink: 0; display: block; }
.plat-logo svg { width: 100%; height: 100%; display: block; }
.source-chip .plat-logo { margin-right: .1rem; }

/* ---------- Tab guide strip: what this tab is for ---------- */
.guide {
    display: flex; align-items: flex-start; gap: .65rem;
    font-size: .93rem; color: var(--muted); line-height: 1.6;
    margin: 0 .25rem 1.35rem .25rem;
}
.guide svg { color: var(--brand-ink); margin-top: .18rem; }
.guide b { color: var(--body); font-weight: 600; }

/* ---------- Headline answer ---------- */
.lede {
    font-family: 'Outfit', sans-serif;
    font-size: 1.35rem; font-weight: 500; line-height: 1.5; color: var(--ink);
    margin: 0; letter-spacing: -.012em;
}
.lede b { font-weight: 700; color: var(--brand-ink); }
.lede-note {
    font-size: .95rem; color: var(--muted); margin: .9rem 0 0 0; line-height: 1.6;
    padding-top: .9rem; border-top: 1px solid var(--line-soft);
}

/* ---------- Stats row (inside one panel, no nested cards) ---------- */
.stat .label {
    display: flex; align-items: center; gap: .4rem;
    font-size: .78rem; font-weight: 600; letter-spacing: .05em;
    text-transform: uppercase; color: var(--muted); margin-bottom: .55rem;
}
.stat .value {
    font-family: 'Outfit', sans-serif;
    font-size: 2.25rem; font-weight: 700; color: var(--ink);
    line-height: 1.05; font-variant-numeric: tabular-nums; letter-spacing: -.025em;
}
.stat .foot { font-size: .88rem; color: var(--muted); margin-top: .45rem; line-height: 1.5; }

/* ---------- Numbered insight rows ---------- */
.insight-row { display: flex; gap: .85rem; padding: .95rem 0; border-top: 1px solid var(--line-soft); }
.insight-row:first-child { border-top: none; padding-top: 0; }
.insight-row:last-child { padding-bottom: 0; }
.insight-row .num {
    flex-shrink: 0; width: 26px; height: 26px; border-radius: 8px;
    display: grid; place-items: center;
    background: var(--brand-soft); color: var(--brand-ink);
    font-size: .8rem; font-weight: 700;
    box-shadow: inset 0 0 0 1px var(--brand-line);
}
.insight-row p { margin: 0; font-size: .97rem; line-height: 1.62; color: var(--body); }
.insight-row p strong { color: var(--ink); font-weight: 600; }

/* ---------- Evidence cards (glass, sit directly on the backdrop) ---------- */
.evidence {
    background: var(--glass);
    -webkit-backdrop-filter: var(--glass-blur);
    backdrop-filter: var(--glass-blur);
    border-radius: var(--radius-lg);
    padding: 1.2rem 1.3rem;
    margin-bottom: 1.1rem;
    box-shadow: var(--glass-ring), var(--glass-edge), var(--glass-shadow);
    transition: transform var(--ease), box-shadow var(--ease);
}
.evidence:hover {
    transform: translateY(-2px);
    box-shadow: 0 0 0 1px var(--brand-line), var(--glass-edge), 0 14px 34px -12px rgba(217,43,88,.3);
}
.evidence .meta-top {
    display: flex; align-items: center; justify-content: space-between;
    gap: .5rem; flex-wrap: wrap; margin-bottom: .9rem;
}
.evidence .quote {
    font-size: 1rem; line-height: 1.65; color: var(--ink);
    padding-left: .95rem; border-left: 2px solid var(--brand-line);
    margin-bottom: .95rem;
}
.evidence .workaround {
    display: flex; gap: .55rem; align-items: flex-start;
    background: var(--brand-soft);
    border-radius: var(--radius-md);
    padding: .65rem .8rem;
    font-size: .89rem; color: var(--body); line-height: 1.55;
    margin-bottom: .9rem;
}
.evidence .workaround svg { color: var(--brand-ink); flex-shrink: 0; margin-top: 3px; }
.evidence .meta-bot {
    display: flex; align-items: center; justify-content: space-between;
    gap: .5rem; flex-wrap: wrap;
    padding-top: .8rem; border-top: 1px solid var(--line-soft);
    font-size: .85rem; color: var(--muted);
}

/* ---------- Live extraction result ---------- */
.extract-quote {
    display: flex; gap: .7rem; align-items: flex-start;
    background: var(--brand-soft);
    border-radius: var(--radius-lg);
    padding: .9rem 1.1rem;
    font-size: 1rem; line-height: 1.6; color: var(--ink);
}
.extract-quote svg { flex-shrink: 0; margin-top: .28rem; }
.extract-grid {
    display: grid; grid-template-columns: repeat(auto-fit, minmax(190px, 1fr));
    gap: 0 1.4rem;
}
.extract-grid .cell {
    display: flex; flex-direction: column; gap: .15rem;
    padding: .7rem 0;
    border-top: 1px solid var(--line-soft);
}
.extract-grid .k {
    font-size: .74rem; font-weight: 600; letter-spacing: .05em;
    text-transform: uppercase; color: var(--muted);
}
.extract-grid .v { font-size: .97rem; color: var(--ink); line-height: 1.5; }

/* ---------- Tags & pills ---------- */
.src { display: inline-flex; align-items: center; gap: .45rem; font-size: .85rem; font-weight: 600; color: var(--body); }
.src .dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
.sev {
    display: inline-flex; align-items: center; gap: .35rem;
    padding: .22rem .6rem; border-radius: var(--radius-sm);
    font-size: .8rem; font-weight: 600;
}
.sev-high { background: rgba(217, 45, 32, .1);  color: #A9231A; box-shadow: inset 0 0 0 1px rgba(217,45,32,.22); }
.sev-med  { background: rgba(181, 113, 0, .11); color: #8A5300; box-shadow: inset 0 0 0 1px rgba(181,113,0,.24); }
.sev-low  { background: rgba(28, 30, 46, .06);  color: #4B4E62; box-shadow: inset 0 0 0 1px rgba(28,30,46,.12); }
.tag {
    display: inline-block; padding: .22rem .6rem; border-radius: var(--radius-sm);
    background: rgba(28, 30, 46, .05); box-shadow: inset 0 0 0 1px rgba(28,30,46,.1);
    font-size: .8rem; font-weight: 500; color: var(--body);
}

/* ---------- Workaround cards ---------- */
.wa-card {
    background: var(--glass);
    -webkit-backdrop-filter: var(--glass-blur);
    backdrop-filter: var(--glass-blur);
    border-radius: var(--radius-lg); padding: 1.05rem 1.15rem;
    margin-bottom: .9rem; height: 100%;
    box-shadow: var(--glass-ring), var(--glass-edge), var(--glass-shadow);
}
.wa-card .txt { font-size: .95rem; color: var(--ink); line-height: 1.6; }
.wa-card .cnt {
    font-size: .82rem; color: var(--brand-ink); margin-top: .6rem;
    font-weight: 600; font-variant-numeric: tabular-nums;
}

/* ---------- Section nav: a floating glass segmented control ---------- */
.st-key-navbar {
    background: var(--glass-strong);
    -webkit-backdrop-filter: var(--glass-blur);
    backdrop-filter: var(--glass-blur);
    padding: .35rem !important;
    border-radius: 15px;
    box-shadow: var(--glass-ring), var(--glass-edge), 0 6px 20px -10px rgba(28,30,46,.22);
    margin-bottom: 1.9rem;
}
.st-key-navbar div[role="radiogroup"] { gap: .2rem; flex-wrap: nowrap; overflow-x: auto; }
.st-key-navbar div[role="radiogroup"] > label {
    background: transparent;
    box-shadow: none;
    border-radius: 11px;
    padding: 0 1.05rem !important;
    min-height: 42px;
    white-space: nowrap;
    transition: color var(--ease), background var(--ease), box-shadow var(--ease);
}
.st-key-navbar div[role="radiogroup"] > label:hover { background: rgba(28,30,46,.05); }
.st-key-navbar div[role="radiogroup"] > label p {
    font-size: .95rem !important; font-weight: 500; color: var(--muted) !important;
}
.st-key-navbar div[role="radiogroup"] > label:has(input:checked) {
    background: #FFFFFF;
    box-shadow: 0 1px 3px rgba(28,30,46,.12);
}
.st-key-navbar div[role="radiogroup"] > label:has(input:checked) p {
    color: var(--brand-ink) !important; font-weight: 600;
}

/* ---------- Pill selector (radio) ---------- */
div[role="radiogroup"] { flex-direction: row; gap: .5rem; flex-wrap: wrap; }
div[role="radiogroup"] > label {
    background: rgba(255,255,255,.6);
    box-shadow: inset 0 0 0 1px rgba(28,30,46,.09);
    border: none;
    border-radius: 999px;
    padding: .5rem 1.1rem !important;
    margin: 0 !important;
    cursor: pointer;
    transition: background var(--ease), box-shadow var(--ease);
    min-height: 44px;
    display: flex; align-items: center;
}
div[role="radiogroup"] > label:hover { background: rgba(255,255,255,.9); }
div[role="radiogroup"] > label > div:first-child { display: none; }  /* hide the radio dot */
div[role="radiogroup"] > label p { font-size: .95rem !important; font-weight: 500; color: var(--body) !important; }
div[role="radiogroup"] > label:has(input:checked) {
    background: #FFFFFF;
    box-shadow: inset 0 0 0 1.5px var(--brand-line), 0 2px 8px -2px rgba(217,43,88,.28);
}
div[role="radiogroup"] > label:has(input:checked) p { color: var(--brand-ink) !important; font-weight: 600; }
div[data-testid="stRadio"] > label { display: none; }  /* collapsed widget label leaves no gap */

/* ---------- Sidebar ---------- */
section[data-testid="stSidebar"] {
    background: rgba(255,255,255,.72) !important;
    -webkit-backdrop-filter: var(--glass-blur);
    backdrop-filter: var(--glass-blur);
    border-right: 1px solid rgba(28,30,46,.07) !important;
}
section[data-testid="stSidebar"] .block-container { padding-top: 2.25rem; }
.side-title {
    display: flex; align-items: center; gap: .5rem;
    font-family: 'Outfit', sans-serif; font-size: 1.05rem; font-weight: 600;
    color: var(--ink); margin-bottom: .3rem;
}
.provenance {
    font-size: .82rem; color: var(--muted); line-height: 1.5;
    margin-top: .9rem; padding: .65rem .8rem; border-radius: 10px;
    background: rgba(28,30,46,.04); box-shadow: inset 0 0 0 1px rgba(28,30,46,.08);
}
.provenance b { color: var(--body); font-weight: 600; }
.side-note { font-size: .89rem; color: var(--muted); line-height: 1.6; margin-bottom: 1.1rem; }
.slice-card {
    background: rgba(255,255,255,.8);
    box-shadow: inset 0 0 0 1.5px var(--brand-line), 0 4px 14px -8px rgba(217,43,88,.3);
    border-radius: var(--radius-lg);
    padding: 1rem 1.1rem;
}
.slice-card .l {
    font-size: .76rem; color: var(--muted); font-weight: 600;
    text-transform: uppercase; letter-spacing: .05em; margin-bottom: .3rem;
}
.slice-card .v {
    font-family: 'Outfit', sans-serif; font-size: 1.7rem; font-weight: 700;
    color: var(--ink); line-height: 1.05; font-variant-numeric: tabular-nums;
}
.slice-card .n { font-size: .85rem; color: var(--body); margin-top: .35rem; line-height: 1.5; }

/* ---------- Inputs ---------- */
.stTextInput label, .stTextArea label, .stSelectbox label {
    font-size: .89rem !important; font-weight: 600 !important; color: var(--body) !important;
    padding-bottom: .3rem;
}
.stTextInput input, .stTextArea textarea {
    border-radius: var(--radius-md) !important;
    border: none !important;
    box-shadow: inset 0 0 0 1px rgba(28,30,46,.14) !important;
    background: rgba(255,255,255,.85) !important;
    font-size: 1rem !important; color: var(--ink) !important;
    min-height: 46px;
}
.stTextArea textarea { min-height: 120px; line-height: 1.65; }
.stTextInput input:focus, .stTextArea textarea:focus {
    box-shadow: inset 0 0 0 2px var(--brand), 0 0 0 4px rgba(255,63,108,.16) !important;
}
div[data-baseweb="select"] > div {
    border-radius: var(--radius-md) !important;
    border: none !important;
    box-shadow: inset 0 0 0 1px rgba(28,30,46,.14);
    background: rgba(255,255,255,.85) !important;
    min-height: 46px; font-size: .97rem;
}
div[data-baseweb="select"] > div:hover { box-shadow: inset 0 0 0 1px rgba(28,30,46,.26); }

/* ---------- Buttons ---------- */
.stButton button {
    border-radius: var(--radius-md) !important;
    font-weight: 600 !important; font-size: .95rem !important;
    min-height: 46px;
    border: none !important;
    background: rgba(255,255,255,.8) !important;
    box-shadow: inset 0 0 0 1px rgba(28,30,46,.12), 0 1px 2px rgba(28,30,46,.05) !important;
    color: var(--body) !important;
    transition: background var(--ease), box-shadow var(--ease), color var(--ease) !important;
    cursor: pointer;
}
.stButton button:hover {
    background: #FFFFFF !important;
    box-shadow: inset 0 0 0 1.5px var(--brand-line), 0 3px 10px -3px rgba(217,43,88,.3) !important;
    color: var(--brand-ink) !important;
}
.stButton button[kind="primary"] {
    background: var(--brand) !important;
    color: #FFFFFF !important;
    box-shadow: 0 4px 14px -4px rgba(255,63,108,.6) !important;
}
.stButton button[kind="primary"]:hover {
    background: var(--brand-ink) !important;
    color: #FFFFFF !important;
    box-shadow: 0 6px 18px -4px rgba(217,43,88,.65) !important;
}
.stButton button:focus-visible, .stTextInput input:focus-visible {
    outline: 2px solid var(--brand) !important;
    outline-offset: 2px !important;
}

/* Pills draw their keyboard focus ring INSIDE the pill. An outline sits outside
   the element, so the nav's horizontal scroll container clipped everything but
   its right-hand arc - which read as a stray bracket beside the active item.
   :has(:focus-visible) also keeps the ring to keyboard users; :focus-within
   matched a plain mouse click too. */
div[role="radiogroup"] > label:has(input:focus-visible) {
    outline: none !important;
    box-shadow: inset 0 0 0 2px var(--brand) !important;
}
.st-key-navbar div[role="radiogroup"] > label:has(input:focus-visible) {
    box-shadow: inset 0 0 0 2px var(--brand), 0 1px 3px rgba(28, 30, 46, .12) !important;
}

/* ---------- Expander / dataframe / misc ---------- */
[data-testid="stExpander"] {
    background: rgba(255,255,255,.6) !important;
    -webkit-backdrop-filter: var(--glass-blur);
    backdrop-filter: var(--glass-blur);
    border: none !important;
    border-radius: var(--radius-lg) !important;
    box-shadow: var(--glass-ring), var(--glass-edge);
}
[data-testid="stExpander"] summary {
    font-size: .97rem; font-weight: 600; color: var(--body); min-height: 48px;
}
[data-testid="stExpander"] summary:hover { color: var(--brand-ink); }
[data-testid="stDataFrame"] { border-radius: var(--radius-md); overflow: hidden; }
[data-testid="stCaptionContainer"] p { color: var(--muted) !important; font-size: .89rem !important; }
[data-testid="stAlertContainer"] { border-radius: var(--radius-md); font-size: .95rem; }
hr { border-color: var(--line-soft) !important; margin: 2rem 0 !important; }
.spacer-sm { height: .75rem; }
.spacer-md { height: 1.35rem; }
.spacer-lg { height: 2rem; }

@media (prefers-reduced-motion: reduce) {
    * { transition: none !important; animation: none !important; }
}
/* Blur is expensive and can wash out on low-power/forced-colors setups */
@media (prefers-contrast: more) {
    [class*="st-key-p_"], .evidence, .wa-card { background: #FFFFFF; backdrop-filter: none; }
}
@media (max-width: 640px) {
    html { font-size: 16px; }
    .main .block-container { padding-top: 1.25rem; }
    .app-header h1 { font-size: 1.4rem; }
    .lede { font-size: 1.15rem; }
    [class*="st-key-p_"] { padding: 1.25rem 1.15rem !important; border-radius: 18px; }
}
</style>
""",
    unsafe_allow_html=True,
)

# ------------------------------------------------------------------
# Inline SVG icons (Lucide geometry) - used inside custom HTML blocks
# where Streamlit's :material/...: syntax is not available.
# ------------------------------------------------------------------
_ICON_PATHS = {
    "bag": '<path d="M6 2 3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4Z"/><path d="M3 6h18"/><path d="M16 10a4 4 0 0 1-8 0"/>',
    "target": '<circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="2"/>',
    "layers": '<path d="m12 2 9 5-9 5-9-5 9-5Z"/><path d="m3 12 9 5 9-5"/><path d="m3 17 9 5 9-5"/>',
    "bookmark": '<path d="m19 21-7-4-7 4V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2Z"/>',
    "alert": '<path d="m21.7 18-8-14a2 2 0 0 0-3.4 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.7-3Z"/><path d="M12 9v4"/><path d="M12 17h.01"/>',
    "check": '<path d="M22 11.1V12a10 10 0 1 1-5.9-9.1"/><path d="m9 11 3 3L22 4"/>',
    "spark": '<path d="m12 3 1.9 5.8a2 2 0 0 0 1.3 1.3L21 12l-5.8 1.9a2 2 0 0 0-1.3 1.3L12 21l-1.9-5.8a2 2 0 0 0-1.3-1.3L3 12l5.8-1.9a2 2 0 0 0 1.3-1.3Z"/>',
    "wrench": '<path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.8-3.8a6 6 0 0 1-7.9 7.9l-6.9 6.9a2.1 2.1 0 0 1-3-3l6.9-6.9a6 6 0 0 1 7.9-7.9Z"/>',
    "trend": '<path d="M16 7h6v6"/><path d="m22 7-8.5 8.5-5-5L2 17"/>',
    "sliders": '<line x1="21" x2="14" y1="4" y2="4"/><line x1="10" x2="3" y1="4" y2="4"/><line x1="21" x2="12" y1="12" y2="12"/><line x1="8" x2="3" y1="12" y2="12"/><line x1="21" x2="16" y1="20" y2="20"/><line x1="12" x2="3" y1="20" y2="20"/><line x1="14" x2="14" y1="2" y2="6"/><line x1="8" x2="8" y1="10" y2="14"/><line x1="16" x2="16" y1="18" y2="22"/>',
    "compass": '<circle cx="12" cy="12" r="10"/><polygon points="16.2 7.8 14.1 14.1 7.8 16.2 9.9 9.9 16.2 7.8"/>',
    "rocket": '<path d="M4.5 16.5c-1.5 1.3-2 5-2 5s3.7-.5 5-2c.7-.8.7-2 0-2.8a2 2 0 0 0-3 0Z"/><path d="m12 15-3-3a22 22 0 0 1 2-3.9A12.9 12.9 0 0 1 22 2c0 2.7-.8 7.7-6 11a22 22 0 0 1-4 2Z"/><path d="M9 12H4s.5-3 2-4c1.7-1 5 0 5 0"/><path d="M12 15v5s3-.5 4-2c1-1.7 0-5 0-5"/>',
    "quote": '<path d="M17 6H3"/><path d="M21 12H8"/><path d="M21 18H8"/><path d="M3 12v6"/>',
    "info": '<circle cx="12" cy="12" r="10"/><path d="M12 16v-4"/><path d="M12 8h.01"/>',
    "grid": '<rect width="7" height="7" x="3" y="3" rx="1.5"/><rect width="7" height="7" x="14" y="3" rx="1.5"/><rect width="7" height="7" x="14" y="14" rx="1.5"/><rect width="7" height="7" x="3" y="14" rx="1.5"/>',
    "flask": '<path d="M10 2v7.5L4.6 18A2 2 0 0 0 6.3 21h11.4a2 2 0 0 0 1.7-3L14 9.5V2"/><path d="M8.5 2h7"/><path d="M7 15h10"/>',
    "search": '<circle cx="11" cy="11" r="7"/><path d="m21 21-4.3-4.3"/>',
}


# ------------------------------------------------------------------
# Platform marks
# ------------------------------------------------------------------
# Inline SVG reconstructions of the Google Play, App Store and YouTube marks,
# used to attribute each signal to the store it came from. Inline rather than
# linked so the app stays self-contained and works offline. These are the
# trademarks of Google LLC and Apple Inc. respectively; drop the official asset
# in here if you need exact brand-guideline compliance.
#
# Note they are used for *labels only*. Charts keep the validated categorical
# palette: a four-colour mark cannot encode a data series, and YouTube red would
# collide with the severity scale.
_PLATFORM_SVG = {
    # Google Play: four regions meeting at a point inside the play triangle.
    # Vertices are softened with a same-colour round join so the mark does not
    # read as a hard-edged triangle at small sizes.
    "Android": (
        '<g stroke-linejoin="round" stroke-width="34">'
        '<polygon points="76,58 215,134 215,256" fill="#34A853" stroke="#34A853"/>'
        '<polygon points="76,58 215,256 76,454" fill="#4285F4" stroke="#4285F4"/>'
        '<polygon points="76,454 215,256 215,378" fill="#EA4335" stroke="#EA4335"/>'
        '<polygon points="215,134 436,256 215,378" fill="#FBBC04" stroke="#FBBC04"/>'
        "</g>"
    ),
    # App Store: blue squircle with the stylised "A".
    "iOS": (
        '<defs><linearGradient id="appstore-g" x1="0" y1="0" x2="0" y2="1">'
        '<stop offset="0" stop-color="#1AC7FC"/><stop offset="1" stop-color="#1E56E3"/>'
        "</linearGradient></defs>"
        '<rect width="512" height="512" rx="114" fill="url(#appstore-g)"/>'
        '<g stroke="#fff" stroke-width="38" stroke-linecap="round" fill="none">'
        '<path d="M170 355 L266 188"/>'
        '<path d="M300 246 L363 355"/>'
        '<path d="M137 296 H375"/>'
        '<path d="M146 358 L133 380"/>'
        "</g>"
    ),
    # YouTube: rounded red plate with the white play triangle.
    "YouTube": (
        '<path fill="#FF0000" d="M501 132a63 63 0 0 0-44-45C418 76 256 76 256 76s-162 0-201 11a63 63 0 0 0-44 45'
        'c-11 39-11 124-11 124s0 85 11 124a63 63 0 0 0 44 45c39 11 201 11 201 11s162 0 201-11a63 63 0 0 0 44-45'
        'c11-39 11-124 11-124s0-85-11-124z"/>'
        '<polygon fill="#fff" points="204,332 204,180 336,256"/>'
    ),
}


# Drop the official asset in as assets/<file>.svg and it is used instead of the
# reconstruction above - the supported way to get exact brand-guideline fidelity.
_PLATFORM_ASSET = {"iOS": "app-store.svg", "Android": "google-play.svg", "YouTube": "youtube.svg"}


@st.cache_data
def _official_marks():
    marks = {}
    for platform, filename in _PLATFORM_ASSET.items():
        path = os.path.join("assets", filename)
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                marks[platform] = f.read()
    return marks


def platform_logo(platform: str, size: int = 16) -> str:
    """Inline SVG store mark, or an empty string for an unknown source."""
    official = _official_marks().get(platform)
    if official:
        # Size the supplied asset without touching its colours or proportions.
        return (
            f'<span class="plat-logo" style="width:{size}px;height:{size}px;display:inline-block">'
            f"{official}</span>"
        )

    body = _PLATFORM_SVG.get(platform)
    if not body:
        return ""
    return (
        f'<svg viewBox="0 0 512 512" width="{size}" height="{size}" xmlns="http://www.w3.org/2000/svg" '
        f'aria-hidden="true" focusable="false" class="plat-logo">{body}</svg>'
    )


def icon(name: str, size: int = 17, color: str = "currentColor", stroke: float = 1.8) -> str:
    """Return an inline SVG string for use inside custom HTML blocks."""
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" '
        f'fill="none" stroke="{color}" stroke-width="{stroke}" stroke-linecap="round" '
        f'stroke-linejoin="round" aria-hidden="true" focusable="false" '
        f'style="flex-shrink:0;vertical-align:-.15em">{_ICON_PATHS[name]}</svg>'
    )


# ------------------------------------------------------------------
# Layout primitives
# ------------------------------------------------------------------
@contextmanager
def panel(key: str, title: str = "", desc: str = "", icon_name: str = "grid", divider: bool = True):
    """A frosted glass section. Every part of the page is one of these."""
    with st.container(key=f"p_{key}"):
        if title:
            st.markdown(
                f'<div class="panel-head{"" if divider else " bare"}">'
                f'<div class="panel-icon">{icon(icon_name, 17)}</div>'
                f"<div><div class=\"panel-title\">{html.escape(title)}</div>"
                f'{f"<div class=panel-desc>{html.escape(desc)}</div>" if desc else ""}</div></div>',
                unsafe_allow_html=True,
            )
        yield


def guide(text_html: str) -> None:
    """One line at the top of a tab explaining what it is and what to do."""
    st.markdown(f'<div class="guide">{icon("info", 16)}<div>{text_html}</div></div>', unsafe_allow_html=True)


def stat(label: str, value: str, foot: str = "", icon_name: str = "trend") -> None:
    st.markdown(
        f'<div class="stat"><div class="label">{icon(icon_name, 14, MUTED)}{html.escape(label)}</div>'
        f'<div class="value">{html.escape(value)}</div>'
        f'{f"<div class=foot>{html.escape(foot)}</div>" if foot else ""}</div>',
        unsafe_allow_html=True,
    )


def insight_rows(points: list) -> None:
    """points: list of (bold_lead, rest) tuples."""
    st.markdown(
        "".join(
            f'<div class="insight-row"><div class="num">{i + 1}</div>'
            f"<p><strong>{lead}</strong> {rest}</p></div>"
            for i, (lead, rest) in enumerate(points)
        ),
        unsafe_allow_html=True,
    )


# ------------------------------------------------------------------
# Chart builders
# ------------------------------------------------------------------
def _base_layout(fig: go.Figure, height: int, legend: bool = False) -> go.Figure:
    fig.update_layout(
        height=height,
        margin=dict(l=6, r=10, t=6, b=0),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family=CHART_FONT, color=BODY, size=13.5),
        showlegend=legend,
        legend=dict(
            orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0,
            title_text="", font=dict(size=13, color=BODY), bgcolor="rgba(0,0,0,0)",
        ),
        hoverlabel=dict(
            bgcolor="#FFFFFF", bordercolor=LINE,
            font=dict(family=CHART_FONT, color=INK, size=13),
        ),
        bargap=0.4,
        bargroupgap=0.12,
    )
    return fig


def magnitude_bars(labels, values, *, suffix="", row_h=42, hover_noun="signals"):
    """Single-hue horizontal bars with direct value labels.

    Takes rows already in display order (rank 1 first) and reverses the y-axis so
    rank 1 sits at the top. One series, so no legend: the panel title names the
    measure. Magnitude is carried by bar length; the hue carries no extra meaning.
    """
    labels = [str(la) for la in labels]
    values = [float(v) for v in values]
    height = max(180, row_h * len(labels) + 30)
    text = [f"{v:,.1f}{suffix}" if suffix == "%" else f"{v:,.0f}{suffix}" for v in values]
    hover_val = "%{x:,.1f}" if suffix == "%" else "%{x:,.0f}"

    fig = go.Figure(
        go.Bar(
            x=values,
            y=labels,
            orientation="h",
            marker=dict(color=BRAND_INK, cornerradius=5),
            text=text,
            textposition="outside",
            textfont=dict(family=CHART_FONT, size=13, color=BODY),
            cliponaxis=False,
            hovertemplate="<b>%{y}</b><br>" + hover_val + " " + hover_noun + "<extra></extra>",
        )
    )
    _base_layout(fig, height)
    fig.update_xaxes(visible=False, range=[0, (max(values) * 1.26) if values else 1])
    fig.update_yaxes(
        autorange="reversed",     # rank 1 at the top, whatever the trace order
        automargin=True,          # never clip a long category label
        ticklabelstandoff=10,     # breathing room without a whitespace hack
        showgrid=False,
        zeroline=False,
        tickfont=dict(family=CHART_FONT, size=13.5, color=BODY),
        linecolor="rgba(0,0,0,0)",
    )
    return fig


def grouped_platform_bars(plot_df, height=400):
    """Grouped bars, one validated hue per platform. Legend is always present."""
    fig = go.Figure()
    for platform, color in PLATFORM_COLORS.items():
        sub = plot_df[plot_df["Platform"] == platform]
        if sub.empty:
            continue
        fig.add_trace(
            go.Bar(
                name=platform,
                x=sub["Blocker"],
                y=sub["% Share"],
                marker=dict(color=color, cornerradius=4),
                hovertemplate="<b>%{x}</b><br>" + platform + ": %{y:.1f}% of corpus<extra></extra>",
            )
        )
    _base_layout(fig, height, legend=True)
    fig.update_layout(barmode="group", margin=dict(l=6, r=10, t=42, b=0))
    fig.update_xaxes(
        showgrid=False, tickangle=-25, automargin=True,
        tickfont=dict(family=CHART_FONT, size=12.5, color=MUTED),
        linecolor=LINE,
    )
    fig.update_yaxes(
        showgrid=True, gridcolor=LINE, zeroline=False, ticksuffix="%",
        tickfont=dict(family=CHART_FONT, size=12.5, color=MUTED),
        title=dict(text="Share of that platform's blockers", font=dict(size=12.5, color=MUTED)),
    )
    return fig


PLOTLY_CONFIG = {"displayModeBar": False, "responsive": True}

DATA_PATH = "data/extracted.csv"
RECLASSIFIED_PATH = "data/extracted_v3.csv"


def _row_count(path):
    """CSV records, not lines - review text contains embedded newlines."""
    import csv as _csv

    stat = os.stat(path)
    return _cached_row_count(path, stat.st_size, stat.st_mtime)


@st.cache_data(show_spinner=False)
def _cached_row_count(path, _size, _mtime):
    import csv as _csv

    with open(path, encoding="utf-8", newline="") as f:
        return max(0, sum(1 for _ in _csv.reader(f)) - 1)


def resolve_dataset():
    """Pick the dataset to read, and say plainly which one and why.

    The reclassification run writes extracted_v2.csv incrementally, so a partial
    file must never be shown as if it were the corpus - every percentage would be
    computed against a fraction of the data. v2 is only used once it covers at
    least as many rows as v1.
    """
    if not os.path.exists(RECLASSIFIED_PATH):
        return DATA_PATH, "original", ""
    try:
        v1, v2 = _row_count(DATA_PATH), _row_count(RECLASSIFIED_PATH)
    except OSError:
        return DATA_PATH, "original", ""
    if v2 >= v1:
        return RECLASSIFIED_PATH, "reclassified", ""
    return DATA_PATH, "original", (
        f"A reclassification run is in progress ({v2:,} of {v1:,} rows). "
        "Showing the original dataset until it completes."
    )


# ------------------------------------------------------------------
# Data loading & secrets
# ------------------------------------------------------------------
# The extractor emits both canonical bucket keys and the short alias forms from
# taxonomy.ALIASES, so `price` and `price_waiting` arrive as separate keys that
# share one display label. Folding them here keeps every chart, the opportunity
# score and the headline counting the same thing.
CANONICAL_KEYS = {
    "price": "price_waiting",
    "quality": "quality_authenticity_doubt",
    "fit": "fit_size_uncertainty",
    "availability": "out_of_stock",
    # The extractor occasionally emits a delivery key. Delivery is not one of the
    # eleven buckets, so it folds into the residual rather than becoming a 12th row.
    "delivery_returns": "other",
    "styling": "styling_uncertainty",
    "uncertainty": "other",
    "uncertainty_type": "other",
}


@st.cache_data
def load_data(path=DATA_PATH):
    if not os.path.exists(path):
        return None
    df = pd.read_csv(path)
    if "id" in df.columns:
        before = len(df)
        df = df.drop_duplicates(subset="id", keep="last")
        if len(df) != before:
            df.attrs["dupes_dropped"] = before - len(df)
    df["relevant"] = df["relevant"].astype(str).str.lower().isin(["true", "1"])

    for col in ("save_motive", "current_blocker"):
        cleaned = df[col].astype(str).str.strip().str.lower()
        df[col] = cleaned.replace(CANONICAL_KEYS).where(df[col].notna())

    # Free-text channel names only differ by case ("Myntra" vs "myntra").
    df["external_channel"] = df["external_channel"].astype(str).str.strip().str.lower().where(
        df["external_channel"].notna()
    )
    return df


def bridge_secrets():
    for name in ("GEMINI_API_KEY", "GROQ_API_KEY"):
        if name in os.environ:
            continue
        try:
            os.environ[name] = st.secrets[name]
        except Exception:
            pass


bridge_secrets()

# ------------------------------------------------------------------
# Bucket accounting
# ------------------------------------------------------------------
# Residual buckets are shown - never dropped - but they are a property of the
# taxonomy rather than a finding, so they are folded into one row that always
# sorts last and never leads a ranking or the headline.
RESIDUAL_KEYS = {"other", "none", "nan", "unclear", "unspecified", "uncertainty", "uncertainty_type", ""}
RESIDUAL_LABEL = "Other / unspecified"

# "not_applicable" is NOT a residual bucket. It means the question does not apply
# to that row - a shopper describing a failed delivery never saved anything, so
# there is no save motive to report. Charting it alongside the buckets would read
# as a classification failure; it is excluded from the motive chart and its count
# is stated instead.
NOT_APPLICABLE = "not_applicable"


def _label_frame(series, drop=()):
    """Clean keys, drop blanks and any excluded values, split residual from named."""
    keys = series.dropna().astype(str).str.strip().str.lower()
    keys = keys[keys != ""]
    if drop:
        keys = keys[~keys.isin(drop)]
    return keys, keys.isin(RESIDUAL_KEYS)


def count_value(series, value):
    """How many rows carry exactly this key."""
    return int((series.dropna().astype(str).str.strip().str.lower() == value).sum())


def ranked_counts(series, n=99, normalize=False, denom=None, drop=()):
    """Counts by *display label*, residual buckets folded into one row at the bottom.

    Aggregating on the label rather than the raw key matters: the extractor emits
    both `price` and `price_waiting`, which share one label. Counting by key would
    draw them as two bars with the same name.

    `n` defaults high so nothing is silently hidden - pass a smaller number only
    where the chart genuinely cannot fit every bucket.

    `denom` sets the base for percentages. Pass the slice size (not the number of
    non-null values) so a share here means the same thing as a share anywhere else
    in the app; the bars then sum to under 100% by exactly the not-recorded share,
    which each caller states.
    """
    keys, residual = _label_frame(series, drop)
    total = len(keys)
    if not total:
        return pd.Series(dtype=float)

    named = keys[~residual].map(bucket_label).value_counts().head(n)
    residual_n = int(residual.sum())

    if normalize:
        base = denom if denom else total
        named = named / base * 100
        residual_n = residual_n / base * 100

    if residual_n:
        named = pd.concat([named, pd.Series({RESIDUAL_LABEL: residual_n})])
    return named


def leading_label(series, drop=()):
    """Label, count and total for the top *named* bucket - used in headline copy."""
    keys, residual = _label_frame(series, drop)
    named = keys[~residual].map(bucket_label).value_counts()
    if named.empty:
        return "—", 0, max(1, len(keys))
    return named.index[0], int(named.iloc[0]), max(1, len(keys))


def residual_breakdown(series):
    """Exactly which raw keys ended up in the Other / unspecified row."""
    keys, residual = _label_frame(series)
    return keys[residual].value_counts(), len(keys)


def share(frame, column, *keys, base=None):
    """Percentage of `keys` in `column`, over an explicit denominator.

    Percentages in this corpus are only meaningful with their base stated: the
    same bucket is a different number over "all relevant signals" than over
    "signals with a blocker recorded". Every caller passes `base` deliberately.
    """
    col = frame[column].dropna().astype(str).str.strip().str.lower()
    denom = len(frame) if base is None else len(base)
    n = int(col.isin(keys).sum())
    return n, denom, (n / denom * 100 if denom else 0.0)


def stated(frame, column, drop=("none", "nan", "unclear", "")):
    """Rows where the model actually recorded a value for `column`."""
    col = frame[column].dropna().astype(str).str.strip().str.lower()
    return col[~col.isin(drop)]


# ------------------------------------------------------------------
# Opportunity scoring
# ------------------------------------------------------------------
SEVERITY_WEIGHT = {"high": 3, "medium": 2, "low": 1}

COVERAGE_GAP = {
    "fit_size_uncertainty": 0.5,
    "in_app_comparison": 0.9,
    "cross_platform_comparison": 0.8,
    "occasion_pending": 0.9,
    "gifting": 0.9,
    "styling_uncertainty": 0.6,
    "quality_authenticity_doubt": 0.5,
    "out_of_stock": 0.4,
}


# ------------------------------------------------------------------
# The business metric
# ------------------------------------------------------------------
BUSINESS_METRIC = (
    "Increase the percentage of users who purchase at least one item from "
    "their wishlist within 30 days of adding it."
)

# Three properties of that metric decide how much a blocker actually costs, and
# none of them is "how often does it appear":
#
#   users, not items   - the denominator is people. A blocker that annoys one
#                        shopper ten times still only costs one user.
#   at least ONE       - a shopper with eight saved items needs a single one to
#                        convert. A blocker on one product is survivable; a doubt
#                        about Myntra itself blocks all eight at once.
#   within 30 days     - "waiting for the Diwali sale" is a real purchase that
#                        lands outside the window. Solving it does not move this
#                        metric, and pretending otherwise inflates the case.
#
# `blocker_scope` and `resolves_in_30d` are LLM-assigned per signal by
# scripts/scope_tag.py, so the two adjustments below are measured on this corpus
# rather than assumed.


def wilson_ci(k, n, z=1.96):
    """95% CI for a proportion. Small buckets need the interval, not the point."""
    if not n:
        return 0.0, 0.0
    p = k / n
    d = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / d
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return max(0.0, (centre - half)) * 100, min(1.0, (centre + half)) * 100


def _tagged_fraction(frame, column, *values):
    """Share of rows carrying one of `values`, over rows actually tagged.

    Untagged rows leave the denominator rather than counting as a "no", so a
    partial tagging run understates nothing.
    """
    if column not in frame.columns:
        return None, 0
    col = frame[column].astype(str).str.strip().str.lower()
    col = col[col.isin({"item", "platform", "yes", "no", "unclear"})]
    if col.empty:
        return None, 0
    return col.isin(values).mean(), len(col)


# Where a complaint was written changes how it is phrased, independently of the
# blocker behind it. An app reviewer writes "always out of stock"; a YouTube
# commenter looking at one garment writes "sold out in M". Pooling the two puts
# out_of_stock at 87% wishlist-wide on app reviews against 30% on YouTube - a
# 57pp swing driven by venue, not by the blocker.
#
# So the weights are estimated on YouTube alone: comments on try-on hauls are the
# closest thing in this corpus to a shopper deliberating over a saved item. The
# ordering is unchanged by the control (quality stays far more wishlist-wide than
# fit), only the level is - which is exactly what a venue artifact looks like.
SCOPE_SOURCE = "youtube"
MIN_TAGGED = 25


@st.cache_data
def scope_weights(_corpus_id=None):
    """Per-bucket (blocks-whole-wishlist, resolves-in-30-days), source-controlled."""
    base = rel[rel["source"].astype(str).str.lower() == SCOPE_SOURCE]
    out = {}
    for key in BUCKETS:
        sub = base[base["current_blocker"] == key]
        plat, n_p = _tagged_fraction(sub, "blocker_scope", "platform")
        in30, n_i = _tagged_fraction(sub, "resolves_in_30d", "yes")
        # Too thin to estimate from is left unestimated rather than guessed.
        out[key] = (
            plat if (plat is not None and n_p >= MIN_TAGGED) else None,
            in30 if (in30 is not None and n_i >= MIN_TAGGED) else None,
            min(n_p, n_i),
        )
    return out


def metric_leverage(df, substitution=0.5):
    """Rank buckets by how much fixing them could move the business metric.

        leverage = share x severity x user-cost x in-window

    `user-cost` is where this parts company with raw frequency. A doubt about
    Myntra itself costs the whole user - every saved item is tainted at once. An
    item-scoped doubt only costs them if they do not simply buy something else
    from the same wishlist, which is what `substitution` estimates. At
    substitution=0 the two are treated alike and this collapses back to
    frequency x severity.
    """
    rel_df = df[df["relevant"]] if "relevant" in df.columns else df
    if rel_df.empty:
        return pd.DataFrame()
    total = len(rel_df)
    weights = scope_weights()

    rows = []
    for key in BUCKETS:
        if key == "other":
            continue
        subset = rel_df[rel_df["current_blocker"] == key]
        if subset.empty:
            continue

        count = len(subset)
        pct = count / total * 100
        lo, hi = wilson_ci(count, total)
        avg_sev = subset["severity"].map(SEVERITY_WEIGHT).dropna().mean()
        avg_sev = float(avg_sev) if pd.notna(avg_sev) else 1.0

        plat, in30, n_tagged = weights.get(key, (None, None, 0))
        # An unestimated bucket takes the conservative reading, never the
        # flattering one: item-scoped, and fully inside the window.
        plat_v = 0.0 if plat is None else plat
        in30_v = 1.0 if in30 is None else in30

        user_cost = plat_v + (1 - plat_v) * (1 - substitution)
        leverage = pct * avg_sev * user_cost * in30_v * (1 if is_addressable(key) else 0)

        rows.append({
            "Opportunity": bucket_label(key),
            "_key": key,
            "Share": pct,
            "_lo": lo,
            "_hi": hi,
            "Signals": count,
            "Avg severity": round(avg_sev, 2),
            "Blocks whole wishlist": float("nan") if plat is None else plat * 100,
            "Resolves in 30d": float("nan") if in30 is None else in30 * 100,
            "Leverage": round(leverage, 1),
            "_estimated": n_tagged >= MIN_TAGGED,
        })

    if not rows:
        return pd.DataFrame()
    out = pd.DataFrame(rows).sort_values("Leverage", ascending=False).reset_index(drop=True)

    # Buckets whose confidence intervals overlap are tied, not ranked. Printing
    # 1, 2, 3 down a list the data cannot separate is the easiest way to mislead
    # a reader who is skimming.
    ranks, rank, prev_lo = [], 0, None
    for _, r in out.iterrows():
        if prev_lo is None or r["_hi"] < prev_lo:
            rank += 1
            prev_lo = r["_lo"]
        else:
            prev_lo = min(prev_lo, r["_lo"])
        ranks.append(rank)
    out["Rank"] = ranks
    return out


def score_opportunities(df):
    rel_df = df[df["relevant"]] if "relevant" in df.columns else df
    if rel_df.empty:
        return pd.DataFrame()

    rows = []
    total = len(rel_df)

    for key in BUCKETS:
        if key == "other":
            continue

        subset = rel_df[rel_df["current_blocker"] == key]
        if subset.empty:
            continue

        count = len(subset)
        pct = count / total * 100

        sev_scores = subset["severity"].map(SEVERITY_WEIGHT).dropna()
        avg_sev = sev_scores.mean() if len(sev_scores) else 1.0

        addressable = is_addressable(key)
        gap = COVERAGE_GAP.get(key, 0.5)
        score = pct * avg_sev * gap * (1 if addressable else 0)

        rows.append(
            {
                "Opportunity": bucket_label(key),
                "Share": pct,
                "Signals": count,
                "Avg severity": round(float(avg_sev), 2),
                "Score": round(score, 1),
            }
        )

    if not rows:  # a narrow segment can match no scoreable bucket at all
        return pd.DataFrame()
    return pd.DataFrame(rows).sort_values("Score", ascending=False)


# ------------------------------------------------------------------
# Load dataset
# ------------------------------------------------------------------
ACTIVE_PATH, DATA_LABEL, DATA_NOTE = resolve_dataset()
df = load_data(ACTIVE_PATH)

if df is None:
    st.error("No dataset found at `data/extracted.csv`. Run the extraction pipeline first.")
    st.stop()

rel = df[df["relevant"]]


def platform_of(source: str) -> str:
    s = str(source)
    if s.startswith("appstore"):
        return "iOS"
    if s == "playstore":
        return "Android"
    if s == "youtube":
        return "YouTube"
    return "Other"


# ------------------------------------------------------------------
# Header
# ------------------------------------------------------------------
_src_counts = df["source"].apply(platform_of).value_counts()
_chips = "".join(
    f'<span class="source-chip">{platform_logo(p, 17)}'
    f"{PLATFORM_NAMES[p]} · {int(_src_counts.get(p, 0)):,}</span>"
    for p in ("iOS", "Android", "YouTube")
)

st.markdown(
    f"""
<div class="app-header">
  <div class="brand">
    <div class="brand-mark">{icon("bag", 24, BRAND_INK)}</div>
    <div>
      <h1>Wishlist Discovery Engine</h1>
      <div class="sub">Why {len(df):,} shoppers save items — and what stops them buying.</div>
    </div>
  </div>
  <div class="source-strip">{_chips}</div>
</div>
""",
    unsafe_allow_html=True,
)

# ------------------------------------------------------------------
# Sidebar: segment filters
# ------------------------------------------------------------------
st.sidebar.markdown(
    f'<div class="side-title">{icon("sliders", 17, BRAND_INK)}Segment filters</div>'
    '<div class="side-note">Narrow the corpus to one shopper segment. Every chart, table '
    "and quote in the app follows this slice.</div>",
    unsafe_allow_html=True,
)

FILTER_KEYS = ("f_gender", "f_category", "f_occasion")

genders = ["All"] + sorted(rel["segment_gender"].dropna().unique().tolist())
gender = st.sidebar.selectbox("Shopper gender", genders, key="f_gender")

categories = ["All"] + sorted(rel["segment_category"].dropna().unique().tolist())
category = st.sidebar.selectbox("Apparel category", categories, key="f_category")

occasions = ["All"] + sorted(rel["segment_occasion"].dropna().unique().tolist())
occasion = st.sidebar.selectbox("Occasion / use case", occasions, key="f_occasion")

view = rel.copy()
if gender != "All":
    view = view[view["segment_gender"] == gender]
if category != "All":
    view = view[view["segment_category"] == category]
if occasion != "All":
    view = view[view["segment_occasion"] == occasion]

_active = [f for f in (gender, category, occasion) if f != "All"]
_share = (len(view) / len(rel) * 100) if len(rel) else 0

st.sidebar.markdown('<div class="spacer-sm"></div>', unsafe_allow_html=True)
st.sidebar.markdown(
    '<div class="slice-card"><div class="l">Active slice</div>'
    f'<div class="v">{len(view):,}</div><div class="n">'
    + (
        f"{_share:.0f}% of {len(rel):,} signals · " + " · ".join(html.escape(a) for a in _active)
        if _active
        else f"All {len(rel):,} relevant signals · no filters applied"
    )
    + "</div></div>",
    unsafe_allow_html=True,
)


st.sidebar.markdown(
    f'<div class="provenance"><b>Dataset</b> {html.escape(DATA_LABEL)}'
    f'{" · " + html.escape(DATA_NOTE) if DATA_NOTE else ""}</div>',
    unsafe_allow_html=True,
)


def reset_filters():
    for key in FILTER_KEYS:
        st.session_state[key] = "All"


if _active:
    st.sidebar.markdown('<div class="spacer-sm"></div>', unsafe_allow_html=True)
    st.sidebar.button(
        "Clear all filters", on_click=reset_filters, width="stretch", icon=":material/filter_alt_off:"
    )

if view.empty:
    st.warning("No signals match this segment. Widen the filters in the sidebar to continue.")
    st.stop()

# ------------------------------------------------------------------
# Precomputed headline figures (recomputed per filter slice)
# ------------------------------------------------------------------
blocker_counts = view["current_blocker"].dropna().value_counts()

# ONE denominator for every percentage in the app: signals in the current slice.
# Mixing bases (all signals vs. signals-with-a-blocker vs. stated-uncertainties)
# is what makes two true numbers for the same bucket disagree, so it is not done.
BASE_N = len(view)

# Headline copy names the leading *named* bucket. "Other / unspecified" is a
# residual of the taxonomy, not a finding, so it never leads the sentence.
top_blocker_label, top_blocker_n, _ = leading_label(view["current_blocker"])
top_blocker_share = top_blocker_n / BASE_N * 100 if BASE_N else 0
top_motive_label, _, _ = leading_label(view["save_motive"], drop=(NOT_APPLICABLE,))

named_blockers = blocker_counts[[k for k in blocker_counts.index if str(k).lower() not in RESIDUAL_KEYS]]
top2_share = (named_blockers.head(2).sum() / BASE_N * 100) if BASE_N else 0

# Two claims that must not be conflated:
#   `is_addressable` only excludes the residual "other" bucket, so "addressable"
#   means "landed in a named bucket" - it is NOT a statement about solvability.
#   Waiting for a price drop is a named bucket but is precisely the blocker a
#   product change cannot fix without discounting, so it is excluded separately.
_price_n = int(blocker_counts.get("price_waiting", 0))
no_discount_n = int(sum(c for k, c in blocker_counts.items() if is_addressable(str(k)))) - _price_n
no_discount_share = (no_discount_n / BASE_N * 100) if BASE_N else 0
top_price_share = (_price_n / BASE_N * 100) if BASE_N else 0
# Everything left: the catch-all, an explicit "no blocker", or no blocker recorded.
unresolved_n = BASE_N - no_discount_n - _price_n
unresolved_share = (unresolved_n / BASE_N * 100) if BASE_N else 0
# Two kinds of evidence, deliberately not pooled: someone describing a wishlist
# they are sitting on, vs someone describing friction they already hit that would
# deter them next time. v1 has no signal_type column, so this stays empty there.
REBUCKETED_N = int((df.get("rebucket_confidence", pd.Series(dtype=str)).fillna("") != "").sum())
DROPPED_N = int((df.get("dropped_category", pd.Series(dtype=str)).fillna("") != "").sum())

HAS_SIGNAL_TYPE = "signal_type" in view.columns and view["signal_type"].notna().any()
if HAS_SIGNAL_TYPE:
    _st = view["signal_type"].dropna().astype(str).str.strip().str.lower()
    OBSERVED_N = int(_st.isin(["unresolved_doubt", "observed_hesitation"]).sum())
    DETERRENT_N = int(_st.isin(["proven_doubt", "deterrent_experience"]).sum())
else:
    OBSERVED_N = DETERRENT_N = 0

high_sev_share = (view["severity"] == "high").mean() * 100 if len(view) else 0
low_conf = (view["confidence"] == "low").sum()
confidence_rate = ((len(view) - low_conf) / len(view) * 100) if len(view) else 0

# ------------------------------------------------------------------
# Section navigation
# ------------------------------------------------------------------
# Deliberately NOT st.tabs. A tab's selection lives in the component's own
# client-side state, and a rerun triggered from inside a tab can remount the
# component and silently throw the user back to the first tab - which is exactly
# what happened when switching deep-dive pillars. Driving the selection from
# session state instead makes it survive every rerun by construction, and lets
# the section be deep-linked with ?view=...
SECTIONS = {
    "Overview": ("dashboard", "overview"),
    "Deep dives": ("target", "deep-dives"),
    "AI copilot": ("auto_awesome", "copilot"),
    "Voice of customer": ("format_quote", "voice"),
    "How it works": ("science", "method"),
}
_SLUG_TO_SECTION = {slug: name for name, (_, slug) in SECTIONS.items()}

if "nav" not in st.session_state:
    st.session_state["nav"] = _SLUG_TO_SECTION.get(st.query_params.get("view", ""), "Overview")


def _sync_nav():
    st.query_params["view"] = SECTIONS[st.session_state["nav"]][1]


# Widgets that only render inside one section would have their state dropped on
# the runs where that section is hidden; re-assigning keeps them alive.
for _k in ("pillar", "copilot_input_box"):
    if _k in st.session_state:
        st.session_state[_k] = st.session_state[_k]

with st.container(key="navbar"):
    nav = st.radio(
        "Section",
        list(SECTIONS),
        key="nav",
        horizontal=True,
        label_visibility="collapsed",
        on_change=_sync_nav,
        format_func=lambda s: f":material/{SECTIONS[s][0]}: {s}",
    )

# ==================================================================
# 1. OVERVIEW
# ==================================================================
if nav == "Overview":
    guide(
        "Read this tab top to bottom. Each panel answers one question, and every number "
        "follows the <b>segment filters</b> panel (open it with the arrow at the top left)."
    )

    with panel("headline", "The headline", "The single most important finding for this segment.", "spark"):
        st.markdown(
            # Motive and blocker share one vocabulary, so the top of both can be the
            # same bucket. Saying it twice reads like a bug; naming the overlap is
            # the actual finding, because it means the doubt was never resolved.
            (
                f'<p class="lede">Shoppers most often save because they are '
                f'<b>{html.escape(top_motive_label.lower())}</b> — and that is still what '
                f"stalls the purchase: the same doubt is the largest named blocker at "
                f"<b>{top_blocker_share:.0f}%</b>, with the top two together holding back "
                f"<b>{top2_share:.0f}%</b> of stalled purchases.</p>"
                if top_motive_label == top_blocker_label else
                f'<p class="lede">The leading reason shoppers save is <b>{html.escape(top_motive_label.lower())}</b>. '
                f"The purchase then stalls on <b>{html.escape(top_blocker_label.lower())}</b> — the largest named "
                f"blocker at <b>{top_blocker_share:.0f}%</b>, with the top two together holding back "
                f"<b>{top2_share:.0f}%</b> of stalled purchases.</p>"
            )
            + f'<p class="lede-note"><b style="color:{INK};">{no_discount_share:.0f}%</b> '
            f"({no_discount_n:,} of {BASE_N:,}) are addressable by product and UX changes alone. "
            f"Another {top_price_share:.0f}% are waiting for a price drop, which no product change fixes "
            f"without discounting. The remaining {unresolved_share:.0f}% hit the taxonomy's catch-all or "
            "had no blocker recorded. Every percentage on this tab is a share of the "
            f"{BASE_N:,} signals in the current slice.</p>",
            unsafe_allow_html=True,
        )

    with panel("kpis", "Key numbers", "The size and quality of the evidence behind everything below.", "layers"):
        k1, k2, k3, k4 = st.columns(4, gap="medium")
        with k1:
            stat("Items analysed", f"{len(df):,}", "Across iOS, Android and YouTube", "layers")
        with k2:
            stat("Wishlist signals", f"{len(view):,}", f"{_share:.0f}% of relevant corpus in view", "bookmark")
        with k3:
            stat("High friction", f"{high_sev_share:.0f}%", "Signals rated high severity", "alert")
        with k4:
            if HAS_SIGNAL_TYPE:
                stat(
                    "Evidence mix",
                    f"{OBSERVED_N / max(1, OBSERVED_N + DETERRENT_N) * 100:.0f}% unresolved",
                    f"{OBSERVED_N:,} still hesitating · {DETERRENT_N:,} already bought and got burned",
                    "layers",
                )
            else:
                stat("Confidence", f"{confidence_rate:.0f}%", "Classified at medium or high confidence", "check")

    c_left, c_right = st.columns(2, gap="medium")

    # Buckets that exist as a reason to save but can never be a reason a purchase
    # is stalled - which is why the two charts do not have the same number of bars.
    motive_only = sorted(
        set(view["save_motive"].dropna().unique())
        - set(view["current_blocker"].dropna().unique())
        - {NOT_APPLICABLE}  # not a bucket - the question simply does not apply
    )

    with c_left:
        with panel(
            "motives",
            "Why customers save",
            f"Every save-motive bucket, as a share of all {BASE_N:,} signals in this slice.",
            "bookmark",
        ):
            _na = count_value(view["save_motive"], NOT_APPLICABLE)
            _motive_base = max(1, BASE_N - _na)
            m_top = ranked_counts(
                view["save_motive"], normalize=True, denom=_motive_base, drop=(NOT_APPLICABLE,)
            )
            st.plotly_chart(
                magnitude_bars(m_top.index, m_top.values, suffix="%", hover_noun="of saved signals"),
                use_container_width=True,
                config=PLOTLY_CONFIG,
                key="chart_motives",
            )
            _m_blank = _motive_base - int(
                view["save_motive"].notna().sum() - _na
            )
            _cap = (
                f"{len(m_top)} buckets · bars total {m_top.sum():.0f}%; the remaining "
                f"{max(0, _m_blank) / _motive_base * 100:.0f}% had no motive recorded."
            )
            if _na:
                _cap += (
                    f" Base is {_motive_base:,}, not {BASE_N:,}: {_na:,} signals describe friction "
                    "the shopper already hit rather than an item they saved, so \"why did they save "
                    "it\" has no answer for them."
                )
            st.caption(_cap)

    with c_right:
        with panel(
            "blockers",
            "What blocks the purchase",
            f"Every blocker bucket, as a share of the same {BASE_N:,} signals.",
            "alert",
        ):
            b_top = ranked_counts(view["current_blocker"], normalize=True, denom=BASE_N)
            st.plotly_chart(
                magnitude_bars(b_top.index, b_top.values, suffix="%", hover_noun="of all signals"),
                use_container_width=True,
                config=PLOTLY_CONFIG,
                key="chart_blockers",
            )
            _b_blank = BASE_N - int(view["current_blocker"].notna().sum())
            _mo = ", ".join(bucket_label(k).lower() for k in motive_only)
            st.caption(
                f"{len(b_top)} buckets · bars total {b_top.sum():.0f}%; the remaining "
                f"{_b_blank / BASE_N * 100:.0f}% ({_b_blank:,} signals) had no blocker recorded."
                + (
                    f" Fewer bars than on the left because {_mo} are reasons to save, never reasons a "
                    "purchase is stalled."
                    if motive_only
                    else ""
                )
            )

    with panel(
        "residual",
        "What is in “Other / unspecified”?",
        "Shoppers describing a real problem that none of the 11 buckets names — audited, not a dumping ground.",
        "info",
    ):
        r_blocker, blocker_n = residual_breakdown(view["current_blocker"])
        r_motive, motive_n = residual_breakdown(view["save_motive"])

        r1, r2 = st.columns(2, gap="medium")
        for col, counts, total_n, name in (
            (r1, r_motive, motive_n, "save motives"),
            (r2, r_blocker, blocker_n, "blockers"),
        ):
            with col:
                if counts.empty:
                    st.markdown(f"**No residual {name}** — every signal landed in a named bucket.")
                    continue
                lines = "".join(
                    f'<div class="insight-row" style="padding:.55rem 0;">'
                    f'<p style="flex:1;"><strong>{html.escape(bucket_label(str(k)))}</strong> '
                    f'<span style="color:{MUTED};">({html.escape(str(k))})</span></p>'
                    f'<p style="font-variant-numeric:tabular-nums;font-weight:600;">{v:,} '
                    f'<span style="color:{MUTED};font-weight:400;">· {v / total_n * 100:.1f}%</span></p></div>'
                    for k, v in counts.items()
                )
                st.markdown(
                    f'<div style="font-size:.85rem;font-weight:600;letter-spacing:.05em;'
                    f'text-transform:uppercase;color:{MUTED};margin-bottom:.5rem;">In {name}</div>{lines}',
                    unsafe_allow_html=True,
                )
        audited = (
            "Every signal in it was re-examined against the 11 buckets: "
            f"{REBUCKETED_N} were re-filed into a bucket that did fit, and {DROPPED_N} were removed from "
            "the corpus entirely as praise, app bugs, creator requests or viewer chatter. "
        ) if (REBUCKETED_N or DROPPED_N) else ""
        st.caption(
            f"{audited}What lands here is a genuine shopping problem with no bucket for it. "
            "`none` is an explicit “no blocker stated”. Neither ever leads a ranking."
        )

    with panel(
        "matrix",
        "What moves the metric",
        "Ranked by effect on wishlist-to-purchase conversion, not by how often people complain.",
        "trend",
    ):
        st.markdown(
            f'<div class="metric-callout"><span>The metric</span>{html.escape(BUSINESS_METRIC)}</div>',
            unsafe_allow_html=True,
        )
        sub_pct = st.slider(
            "If one saved item is blocked, how often does the shopper just buy a different one instead?",
            0, 100, 50, 5, format="%d%%", key="substitution",
            help="At 0% every blocked item costs you the user. At 100% only doubts about Myntra "
                 "itself can cost you the user, because anything item-specific is substituted away.",
        )
        opp_df = metric_leverage(view, substitution=sub_pct / 100)

        if opp_df.empty:
            st.info("No opportunity data for this slice. Widen the filters to see the ranking.")
        else:
            # Streamlit renders a NaN in a NumberColumn as the literal "None".
            # An unestimated cell should read as absent, so these two are
            # formatted to text with an em dash for "too few signals to say".
            show = opp_df[["Rank", "Opportunity", "Share", "Signals", "Avg severity",
                           "Blocks whole wishlist", "Resolves in 30d", "Leverage"]].copy()
            for col in ("Blocks whole wishlist", "Resolves in 30d"):
                show[col] = show[col].map(lambda v: "—" if pd.isna(v) else f"{v:.0f}%")
            st.dataframe(
                show, width="stretch", hide_index=True,
                column_config={
                    "Rank": st.column_config.NumberColumn(
                        "Rank", help="Buckets whose 95% confidence intervals overlap share a rank.",
                        format="%d", width="small"),
                    "Opportunity": st.column_config.TextColumn("Opportunity", width="medium"),
                    "Share": st.column_config.NumberColumn("Share", format="%.1f%%"),
                    "Signals": st.column_config.NumberColumn("Signals", format="%d"),
                    "Avg severity": st.column_config.NumberColumn(
                        "Severity", help="1 = low, 3 = high", format="%.2f"),
                    "Blocks whole wishlist": st.column_config.TextColumn(
                        "Whole wishlist",
                        help="Share of these signals that are a doubt about Myntra itself rather than "
                             "one product, so every saved item is blocked at once. Estimated on YouTube "
                             "comments only, to control for app reviewers phrasing everything as a "
                             "platform complaint. An em dash means too few tagged signals to estimate."),
                    "Resolves in 30d": st.column_config.TextColumn(
                        "In 30 days",
                        help="Share the shopper could plausibly complete inside the measurement window. "
                             "A purchase waiting on a festival sale is real revenue that lands outside it."),
                    "Leverage": st.column_config.ProgressColumn(
                        "Leverage",
                        help="share x severity x user-cost x in-window",
                        format="%.1f", min_value=0,
                        max_value=max(1.0, float(opp_df["Leverage"].max()))),
                },
            )
            tied = opp_df.groupby("Rank").size()
            tied = [r for r, n in tied.items() if n > 1]
            if tied:
                names = opp_df[opp_df["Rank"] == tied[0]]["Opportunity"].tolist()
                joined = (" and ".join(names) if len(names) < 3
                          else ", ".join(names[:-1]) + " and " + names[-1])
                st.caption(
                    f"**{joined}** all share rank {tied[0]}: their 95% confidence intervals "
                    f"overlap at n={len(view):,}, so this corpus cannot separate them. Treat "
                    "them as one priority, not a first, second and third."
                )

    with panel(
        "sizing",
        "What it is worth",
        "Turn the ranking into a range of users, using your funnel numbers.",
        "sliders",
    ):
        st.caption(
            "This corpus measures stated friction, not conversion — it cannot observe how many "
            "wishlists convert. Supply the funnel numbers it is missing and the shares above become "
            "a size. Everything below is a scenario built on your inputs, not a measurement."
        )
        c1, c2 = st.columns(2, gap="medium")
        with c1:
            users = st.number_input(
                "Users adding to a wishlist per month", min_value=1000, value=1_000_000,
                step=50_000, format="%d", key="mau")
            intent = st.slider(
                "Of those who do not buy, how many actually wanted to?", 5, 100, 40, 5,
                format="%d%%", key="intent",
                help="The rest are browsing, saving for later or window shopping. No product fix "
                     "converts them, and counting them is what turns a sizing model into a fantasy.")
        with c2:
            baseline = st.number_input(
                "…who buy at least one saved item within 30 days (%)", min_value=0.1,
                max_value=99.0, value=20.0, step=0.5, key="baseline")
            efficacy = st.slider(
                "Of those blocked, how many does the fix actually convert?", 1, 100, 25, 1,
                format="%d%%", key="efficacy",
                help="The honest unknown. A size guide does not convert everyone who was unsure. "
                     "Anything above ~40% should be treated as optimistic until an A/B test says otherwise.")

        opp_sized = metric_leverage(view, substitution=st.session_state.get("substitution", 50) / 100)
        if opp_sized.empty:
            st.info("No opportunity data for this slice.")
        else:
            # The addressable pool is not everyone who failed to convert. It is the
            # ones who meant to buy and were stopped - which is why `intent` exists.
            blocked = users * (1 - baseline / 100) * (intent / 100)
            lev_total = opp_sized["Leverage"].sum()
            if lev_total > 0:
                sized = opp_sized.head(5).copy()
                sized["held"] = blocked * sized["Leverage"] / lev_total
                sized["won"] = sized["held"] * efficacy / 100
                sized["lift"] = sized["won"] / users * 100
                disp = pd.DataFrame({
                    "Opportunity": sized["Opportunity"],
                    "Users held back / month": sized["held"].map(lambda v: f"{v:,.0f}"),
                    "Recovered / month": sized["won"].map(lambda v: f"{v:,.0f}"),
                    "Metric lift": sized["lift"].map(lambda v: f"+{v:.2f} pp"),
                })
                st.dataframe(
                    disp, width="stretch", hide_index=True,
                    column_config={
                        "Opportunity": st.column_config.TextColumn("Opportunity", width="medium"),
                        "Users held back / month": st.column_config.TextColumn(
                            "Held back / month",
                            help="The blocked pool, split by each bucket's share of total leverage."),
                        "Recovered / month": st.column_config.TextColumn("Recovered / month"),
                        "Metric lift": st.column_config.TextColumn(
                            "Metric lift", help="Percentage points added to the business metric."),
                    },
                )
                total_lift = float(sized["lift"].sum())
                st.markdown(
                    f'<div class="metric-callout"><span>Modelled outcome</span>'
                    f"Fixing the top five moves the metric <b>+{total_lift:.2f} pp</b> — "
                    f"{baseline:.1f}% → <b>{baseline + total_lift:.2f}%</b>, "
                    f"<b>{sized['won'].sum():,.0f}</b> more converting users a month.</div>",
                    unsafe_allow_html=True,
                )
                # A model that promises to move a conversion metric by half its own
                # baseline is describing its inputs, not the business.
                if total_lift > baseline * 0.25:
                    st.warning(
                        f"That is a **{total_lift / baseline * 100:.0f}% relative lift** on the baseline. Conversion "
                        "uplifts above ~25% relative almost never survive contact with an A/B test. "
                        "Lower the intent or efficacy assumption before taking this anywhere."
                    )
                st.caption(
                    "Two assumptions carry this. **One:** blockers are distributed among "
                    "non-converting wishlist users the way they are distributed in this corpus of "
                    "reviewers and commenters — untested, and the largest source of error here. "
                    "**Two:** the leverage split above is a reasonable proxy for how blocked users "
                    "divide. Validate the first against real wishlist telemetry before anyone "
                    "commits a roadmap to these numbers."
                )

    with panel(
        "platforms",
        "Blockers by platform",
        "Where iOS, Android and YouTube audiences diverge. Each bar is a share of that platform's own blockers.",
        "grid",
    ):
        plat = view.copy()
        plat["platform"] = plat["source"].apply(platform_of)
        cross = (
            plat[plat["platform"].isin(PLATFORM_COLORS)]
            .groupby(["platform", "current_blocker"])
            .size()
            .unstack(fill_value=0)
        )

        if cross.empty:
            st.info("Not enough cross-platform data in this slice.")
        else:
            pct_cross = cross.div(cross.sum(axis=1), axis=0) * 100
            # Five named blockers keep the grouped bars legible; residual buckets are dropped.
            keep = [c for c in cross.sum().sort_values(ascending=False).index if str(c).lower() not in RESIDUAL_KEYS][:5]
            pct_cross = pct_cross[keep]
            pct_cross.columns = [bucket_label(c) for c in pct_cross.columns]
            plot_df = pct_cross.T.reset_index().rename(columns={"index": "Blocker"})
            plot_df = plot_df.melt(id_vars="Blocker", var_name="Platform", value_name="% Share")
            st.plotly_chart(grouped_platform_bars(plot_df), use_container_width=True, config=PLOTLY_CONFIG, key="chart_platforms")


# ==================================================================
# 2. DEEP DIVES
# ==================================================================
if nav == "Deep dives":
    guide("Pick a pillar below. Each one is a chart plus the reading of it, on a single screen.")

    with panel("pillars", "Strategic deep dives", "Four pillars answering the research brief.", "target"):
        pillar = st.radio(
            "Pillar",
            ["Intent & motives", "Blockers & uncertainty", "Search leakage", "ROI roadmap"],
            key="pillar",
            horizontal=True,
            label_visibility="collapsed",
        )

    # Every pillar below reuses the SAME element keys - "pillarchart", "pillarread"
    # and chart key "chart_pillar" - on purpose. Giving each pillar its own keys
    # changes the element tree's identity when the selection changes, which
    # remounts the enclosing st.tabs component and silently throws the user back
    # to the first tab. Keep these keys identical across all four branches.
    if pillar == "Intent & motives":
        left, right = st.columns([1.15, 1], gap="medium")
        with left:
            with panel(
                "pillarchart",
                "Save motives",
                f"Every intent, as a share of the {max(1, len(rel) - count_value(rel['save_motive'], NOT_APPLICABLE)):,} signals where someone actually saved an item.",
                "bookmark",
            ):
                _na_all = count_value(rel["save_motive"], NOT_APPLICABLE)
                _sm_base = max(1, len(rel) - _na_all)
                sm = ranked_counts(
                    rel["save_motive"], normalize=True, denom=_sm_base, drop=(NOT_APPLICABLE,)
                )
                st.plotly_chart(
                    magnitude_bars(sm.index, sm.values, suffix="%", hover_noun="of all signals"),
                    use_container_width=True,
                    config=PLOTLY_CONFIG,
                    key="chart_pillar",
                )
        with right:
            with panel("pillarread", "What this tells us", "", "spark", divider=False):
                _ws_n, _ws_d, _ws_p = share(rel, "save_motive", "window_shopping", base=rel)
                _cmp_n, _, _cmp_p = share(
                    rel, "save_motive", "in_app_comparison", "cross_platform_comparison", base=rel
                )
                _risk_n, _, _risk_p = share(
                    rel, "save_motive", "price_waiting", "quality_authenticity_doubt",
                    "fit_size_uncertainty", base=rel
                )
                insight_rows(
                    [
                        (
                            "Active risk management.",
                            f"<b>{_risk_p:.0f}%</b> of saves ({_risk_n:,}) are price, quality or fit doubt — "
                            "shoppers deferring financial commitment until they resolve a specific risk, "
                            "not casually bookmarking.",
                        ),
                        (
                            "Real intent, not browsing.",
                            f"Only <b>{_ws_p:.1f}%</b> ({_ws_n:,} signals) are explicit zero-intent window "
                            "shopping — the wishlist is overwhelmingly a considered-purchase list.",
                        ),
                        (
                            "Consideration sets.",
                            f"<b>{_cmp_p:.1f}%</b> ({_cmp_n:,}) save specifically to compare items, in the app "
                            "or against another site.",
                        ),
                    ]
                )
                st.caption(f"Shares are of all {_ws_d:,} relevant signals.")

    elif pillar == "Blockers & uncertainty":
        left, right = st.columns([1.15, 1], gap="medium")
        with left:
            with panel(
                "pillarchart",
                "Residual uncertainty",
                f"What is still unresolved, as a share of all {len(rel):,} relevant signals.",
                "alert",
            ):
                unc = ranked_counts(rel["uncertainty_type"], normalize=True, denom=len(rel))
                st.plotly_chart(
                    magnitude_bars(unc.index, unc.values, suffix="%", hover_noun="of all signals"),
                    use_container_width=True,
                    config=PLOTLY_CONFIG,
                    key="chart_pillar",
                )
        with right:
            with panel("pillarread", "What this tells us", "", "spark", divider=False):
                _qm_n, _base_n, _qm_p = share(rel, "save_motive", "quality_authenticity_doubt", base=rel)
                _qb_n, _, _qb_p = share(rel, "current_blocker", "quality_authenticity_doubt", base=rel)
                _oos_n, _, _oos_p = share(rel, "current_blocker", "out_of_stock", base=rel)
                _shift = _qb_p - _qm_p
                insight_rows(
                    [
                        (
                            "The quality spike.",
                            f"Quality and authenticity doubt is the motive for <b>{_qm_p:.1f}%</b> of saves "
                            f"({_qm_n:,}) but the blocker for <b>{_qb_p:.1f}%</b> ({_qb_n:,}) — a "
                            f"{_shift:+.1f} point rise between saving and checking out, as shoppers read "
                            "critical reviews.",
                        ),
                        (
                            "The stockout trap.",
                            f"<b>{_oos_p:.1f}%</b> ({_oos_n:,}) delay long enough that they return to find "
                            "their exact size gone.",
                        ),
                        (
                            "Postponement drivers.",
                            "Shoppers wait for sale cycles such as Diwali and EORS, or stall because they "
                            "dread the return process if the size is wrong. "
                            "<i>Qualitative — read from the quotes, not counted.</i>",
                        ),
                    ]
                )
                st.caption(f"Shares are of all {_base_n:,} relevant signals.")

    elif pillar == "Search leakage":
        left, right = st.columns([1.15, 1], gap="medium")
        with left:
            with panel(
                "pillarchart",
                "Where shoppers go instead",
                "External channels used to resolve doubt. Signal counts, not shares.",
                "compass",
            ):
                ch = ranked_counts(rel["external_channel"], n=8)
                st.plotly_chart(
                    magnitude_bars(ch.index, ch.values, hover_noun="signals"),
                    use_container_width=True,
                    config=PLOTLY_CONFIG,
                    key="chart_pillar",
                )
                st.caption(
                    "Shown as counts on purpose: only a small minority of signals name a channel at all, "
                    "so a percentage would be misleadingly small against the corpus and misleadingly "
                    "confident against the subset."
                )
        with right:
            with panel("pillarread", "What this tells us", "", "spark", divider=False):
                _named_ch = stated(rel, "external_channel", drop=("none", "nan", "unclear", ""))
                _ch_total = len(_named_ch)
                _rivals = int(_named_ch.isin(["amazon", "flipkart", "meesho", "ajio", "nykaa"]).sum())
                _rival_p = (_rivals / _ch_total * 100) if _ch_total else 0
                _video_n = int(_named_ch.isin(["youtube", "instagram", "social media"]).sum())
                _video_p = (_video_n / _ch_total * 100) if _ch_total else 0
                insight_rows(
                    [
                        (
                            "They leave for rival marketplaces.",
                            f"<b>{_rival_p:.0f}%</b> of named external channels ({_rivals:,} of {_ch_total:,}) "
                            "are Amazon, Flipkart, Meesho, AJIO or Nykaa — visited for customer unboxing "
                            "photos and inch measurements that studio shots hide.",
                        ),
                        (
                            "Video shows up, but rarely in this field.",
                            f"Only <b>{_video_n}</b> signals ({_video_p:.0f}%) name YouTube or social video "
                            "here. The try-on-haul behaviour is visible in the YouTube quotes themselves, "
                            "so treat this field as under-reporting it rather than as evidence against it.",
                        ),
                        (
                            "The multi-order hack.",
                            "With no in-app comparison, shoppers order two or three sizes intending from the "
                            "start to return the losers. <i>Qualitative — read from the quotes, not counted.</i>",
                        ),
                    ]
                )
                st.caption(
                    f"Only {_ch_total:,} of {len(rel):,} signals name an external channel, so these shares "
                    "are of that subset — not of the whole corpus."
                )

    else:
        with panel(
            "p4",
            "Prioritised roadmap",
            "Five interventions, ranked by the signal actually behind them.",
            "rocket",
        ):
            N = len(rel)

            def _sig(column, *keys):
                n, _, p = share(rel, column, *keys, base=rel)
                return n, p

            def _high_sev(*keys):
                sub = rel[rel["current_blocker"].isin(keys)]
                return (sub["severity"] == "high").mean() * 100 if len(sub) else 0.0

            fit_n, fit_p = _sig("current_blocker", "fit_size_uncertainty")
            qual_n, qual_p = _sig("current_blocker", "quality_authenticity_doubt")
            cmp_n, cmp_p = _sig("save_motive", "in_app_comparison", "cross_platform_comparison")
            oos_n, oos_p = _sig("current_blocker", "out_of_stock")
            price_n, price_p = _sig("current_blocker", "price_waiting")
            sty_n, sty_p = _sig("current_blocker", "styling_uncertainty")

            st.markdown(
                f"""
| # | Opportunity | Friction solved | Signal in this corpus | Intervention |
| :- | :--- | :--- | :--- | :--- |
| **1** | **Verified UGC & video hub** | `quality_authenticity_doubt` | **{qual_p:.1f}%** ({qual_n:,}) · #1 blocker · {_high_sev("quality_authenticity_doubt"):.0f}% high severity | Verified customer unboxing photos, daylight fabric zoom, customer try-on video in the wishlist drawer |
| **2** | **Price & restock alerts** | `price_waiting`, `out_of_stock` | **{price_p:.1f}%** ({price_n:,}) price waiting · **{oos_p:.1f}%** ({oos_n:,}) stockouts | One-click WhatsApp restock alerts plus a 48-hour price lock, without discounting |
| **3** | **Interactive fit & size matrix** | `fit_size_uncertainty` | **{fit_p:.1f}%** ({fit_n:,}) · {_high_sev("fit_size_uncertainty"):.0f}% high severity | Cross-brand fit translation (*"fits like Zara M"*), exact inch measurements, body visualiser |
| **4** | **In-wishlist comparison tray** | `in_app_comparison`, `cross_platform_comparison` | **{cmp_p:.1f}%** ({cmp_n:,}) of save motives | Side-by-side spec tray inside the wishlist: fabric, ratings, price, returnability |
| **5** | **'Complete the look' styler** | `styling_uncertainty` | **{sty_p:.1f}%** ({sty_n:,}) · smallest of the five | Algorithmic bundling of matching footwear and bottoms already in inventory, one-click add |
"""
            )
            st.caption(
                f"Every share above is computed live from the corpus, over all {N:,} relevant signals. "
                "This table ranks by raw signal volume and severity. That is not the same as ranking "
                "by effect on the business metric — for that, see **what moves the metric** on the "
                "Overview, which additionally weights each blocker by whether it blocks the whole "
                "wishlist or just one item, and by whether it resolves inside the 30-day window."
            )


# ==================================================================
# 3. AI COPILOT
# ==================================================================
if nav == "AI copilot":
    guide(
        "Type a question, or tap a suggestion. The copilot searches the corpus first, "
        "then answers <b>only from the signals it found</b> — and shows you those signals."
    )

    def set_copilot_prompt(prompt_text):
        st.session_state["copilot_input_box"] = prompt_text
        st.session_state["run_copilot_now"] = True

    st.session_state.setdefault("copilot_input_box", "")
    st.session_state.setdefault("run_copilot_now", False)

    with panel(
        "ask",
        "Ask the corpus",
        f"Any research or product question, put to the {len(rel):,} classified customer signals.",
        "spark",
    ):
        q1, q2, q3 = st.columns(3, gap="small")
        q1.button(
            "Footwear sizing hesitation",
            on_click=set_copilot_prompt,
            args=("Why do users hesitate when buying footwear and what are the main sizing issues?",),
            width="stretch",
        )
        q2.button(
            "Fabric quality complaints",
            on_click=set_copilot_prompt,
            args=("What are the most common complaints about fabric quality, material transparency, and colour bleeding?",),
            width="stretch",
        )
        q3.button(
            "iOS vs Android abandonment",
            on_click=set_copilot_prompt,
            args=("What are the primary reasons iOS users abandon wishlists compared to Android users?",),
            width="stretch",
        )

        st.markdown('<div class="spacer-sm"></div>', unsafe_allow_html=True)

        st.text_input(
            "Your question",
            placeholder="e.g. How does return friction influence checkout? What do women say about ethnic wear?",
            key="copilot_input_box",
        )
        btn_clicked = st.button("Ask the copilot", type="primary", icon=":material/send:")

    should_run = btn_clicked or st.session_state.get("run_copilot_now", False)
    st.session_state["run_copilot_now"] = False

    if not should_run:
        with panel("askhelp", "What you get back", "Every answer comes in these four parts.", "info", divider=False):
            insight_rows(
                [
                    ("An executive summary.", "Two or three sentences answering the question directly."),
                    ("Quantitative patterns.", "Concrete observations drawn from the matched signals, not general knowledge."),
                    ("Verbatim evidence.", "The actual customer quotes behind the answer, each attributed to its source and blocker."),
                    ("A recommendation.", "One product or UX intervention that follows from the evidence."),
                ]
            )
    else:
        query_to_run = st.session_state.get("copilot_input_box", "").strip()
        if not query_to_run:
            st.warning("Enter a question, or pick one of the suggestions above.")
        else:
            with st.spinner("Searching the corpus and synthesising an answer…"):
                try:
                    tokens = [
                        t.lower()
                        for t in re.findall(r"\w+", query_to_run)
                        if len(t) > 2
                        and t.lower() not in {"what", "why", "how", "when", "the", "and", "for", "with", "about", "are", "is"}
                    ]

                    matches = []
                    for _, row in rel.iterrows():
                        score = 0
                        full_str = (
                            f"{row.get('text', '')} {row.get('evidence_quote', '')} {row.get('current_blocker', '')} "
                            f"{row.get('save_motive', '')} {row.get('segment_category', '')} "
                            f"{row.get('segment_gender', '')} {row.get('workaround', '')}"
                        ).lower()
                        for t in tokens:
                            if t in full_str:
                                score += 1
                        if score > 0:
                            matches.append((score, row))

                    matches.sort(key=lambda x: x[0], reverse=True)
                    top_matches = [m[1] for m in matches[:15]]

                    if not top_matches:
                        top_matches = [r for _, r in rel.sample(min(15, len(rel))).iterrows()]

                    quotes_context = []
                    for r in top_matches:
                        q = r.get("evidence_quote") if pd.notna(r.get("evidence_quote")) else r.get("text")
                        src = str(r.get("source", "user"))
                        blk = bucket_label(str(r.get("current_blocker", "")))
                        wa = str(r.get("workaround")) if pd.notna(r.get("workaround")) else "None"
                        quotes_context.append(f'- [{src}] (Blocker: {blk} | Workaround: {wa}) "{q}"')

                    context_str = "\n".join(quotes_context)

                    system_prompt = f"""You are the Chief AI Research Strategist for the Wishlist Discovery Engine analyzing an e-commerce customer corpus of 10,000+ reviews (Myntra, AJIO, iOS App Store, Play Store, YouTube).
Answer the user's question directly, insightfully, and objectively based on the verified customer signals provided below.

Format your response cleanly with these exact section headings (no emoji):
### Executive summary
(2-3 crisp sentences answering the question)
### Key quantitative insights
(bullet points with concrete observations)
### Verbatim customer evidence
(quote 2-3 of the most relevant quotes from the context with attribution)
### Recommendation
(one actionable product or UX proposal)

Context Customer Signals:
{context_str}
"""
                    from llm import LLMRouter

                    router = LLMRouter(verbose=False)
                    answer, provider = router.complete(
                        system_prompt, f"Question: {query_to_run}", max_tokens=1500, json_mode=False
                    )

                    with panel(
                        "answer",
                        "Answer",
                        f"Generated by {provider.upper()} from {len(top_matches)} matched signals.",
                        "spark",
                    ):
                        st.markdown(answer)

                    with panel("evidence_used", "The evidence behind it", "Every signal the answer was built from.", "quote"):
                        for r in top_matches:
                            q_item = r.get("evidence_quote") if pd.notna(r.get("evidence_quote")) else r.get("text")
                            wa = str(r.get("workaround")) if pd.notna(r.get("workaround")) else "None"
                            st.markdown(
                                f'<div style="padding:.85rem 0;border-bottom:1px solid rgba(28,30,46,.07);">'
                                f'<div style="font-size:.97rem;color:{INK};line-height:1.6;">'
                                f'"{html.escape(str(q_item))}"</div>'
                                f'<div style="font-size:.83rem;color:{MUTED};margin-top:.4rem;">'
                                f"{html.escape(str(r.get('source')).upper())} · "
                                f"{html.escape(bucket_label(str(r.get('current_blocker'))))} · "
                                f"workaround: {html.escape(wa)}</div></div>",
                                unsafe_allow_html=True,
                            )

                except Exception as ex:
                    st.error(f"Could not generate an answer: {ex}")


# ==================================================================
# 4. VOICE OF CUSTOMER
# ==================================================================
if nav == "Voice of customer":
    guide("Set the filters, then read the quotes. Each card is one customer signal with the labels the model gave it.")

    with panel("vocfilters", "Find the evidence", "Narrow by blocker, severity or channel, or search the text.", "search"):
        ec1, ec2, ec3, ec4 = st.columns([3, 2, 2, 3], gap="small")

        with ec1:
            blocker_options = sorted(view["current_blocker"].dropna().unique().tolist())
            selected_blocker = st.selectbox(
                "Blocker",
                ["All"] + blocker_options,
                format_func=lambda x: "All blockers"
                if x == "All"
                else f"{bucket_label(x)} ({len(view[view['current_blocker'] == x])})",
            )
        with ec2:
            selected_sev = st.selectbox(
                "Severity", ["All", "high", "medium", "low"],
                format_func=lambda x: "All severities" if x == "All" else x.capitalize(),
            )
        with ec3:
            selected_source = st.selectbox(
                "Channel", ["All", "playstore", "appstore", "youtube"],
                format_func=lambda x: {
                    "All": "All channels",
                    "playstore": PLATFORM_NAMES["Android"],
                    "appstore": PLATFORM_NAMES["iOS"],
                    "youtube": PLATFORM_NAMES["YouTube"],
                }[x],
            )
        with ec4:
            search_query = st.text_input("Search quotes", placeholder="size, kurta, refund, fabric…")

    q_df = view.copy()
    if selected_blocker != "All":
        q_df = q_df[q_df["current_blocker"] == selected_blocker]
    if selected_sev != "All":
        q_df = q_df[q_df["severity"] == selected_sev]
    if selected_source != "All":
        if selected_source == "appstore":
            q_df = q_df[q_df["source"].astype(str).str.startswith("appstore")]
        else:
            q_df = q_df[q_df["source"] == selected_source]
    if search_query.strip():
        q_df = q_df[
            q_df["evidence_quote"].astype(str).str.contains(search_query, case=False, na=False)
            | q_df["text"].astype(str).str.contains(search_query, case=False, na=False)
            | q_df["workaround"].astype(str).str.contains(search_query, case=False, na=False)
        ]

    quotes_to_show = q_df.dropna(subset=["evidence_quote"]).head(18)

    st.markdown(
        f'<div style="font-size:.92rem;color:{MUTED};margin:0 .25rem 1.1rem .25rem;">'
        f"<b style=\"color:{BODY};\">{len(q_df):,}</b> signals match · showing {len(quotes_to_show)}</div>",
        unsafe_allow_html=True,
    )

    if quotes_to_show.empty:
        st.info("No quotes match these filters. Clear the search box or widen the blocker and severity filters.")
    else:
        cols = st.columns(2, gap="medium")

        for idx, (_, row) in enumerate(quotes_to_show.iterrows()):
            plat_name = platform_of(row.get("source", ""))
            plat_display = PLATFORM_NAMES.get(plat_name, "Forum / review")
            # Unknown sources have no store mark, so they keep the coloured dot.
            plat_mark = platform_logo(plat_name, 17) or (
                f'<span class="dot" style="background:{MUTED}"></span>'
            )

            sev = str(row.get("severity", "low")).lower()
            sev_class, sev_word = {
                "high": ("sev-high", "High friction"),
                "medium": ("sev-med", "Medium friction"),
            }.get(sev, ("sev-low", "Low friction"))

            blocker_name = bucket_label(str(row.get("current_blocker", "")))
            quote_text = html.escape(str(row.get("evidence_quote", "")))

            workaround_html = ""
            wa_raw = row.get("workaround")
            if pd.notna(wa_raw) and str(wa_raw).strip() and str(wa_raw).lower() not in ("none", "null"):
                workaround_html = (
                    f'<div class="workaround">{icon("wrench", 15)}'
                    f"<span><b>Workaround:</b> {html.escape(str(wa_raw))}</span></div>"
                )

            meta_items = []
            for field in ("segment_gender", "segment_category", "segment_occasion"):
                val = str(row.get(field, "")).strip()
                if val.lower() not in ("unclear", "none", "nan", ""):
                    meta_items.append(html.escape(val))
            meta_str = " · ".join(meta_items) if meta_items else "Segment unspecified"

            with cols[idx % 2]:
                st.markdown(
                    f'<div class="evidence">'
                    f'<div class="meta-top">'
                    f'<span class="src">{plat_mark}{plat_display}</span>'
                    f'<span class="sev {sev_class}">{sev_word}</span>'
                    f"</div>"
                    f'<div class="quote">{quote_text}</div>'
                    f"{workaround_html}"
                    f'<div class="meta-bot"><span class="tag">{html.escape(blocker_name)}</span>'
                    f"<span>{meta_str}</span></div>"
                    f"</div>",
                    unsafe_allow_html=True,
                )

        if len(q_df) > 18:
            st.caption(f"Showing the first 18 of {len(q_df):,} matches. Narrow the search to see specific topics.")

    st.markdown('<div class="spacer-lg"></div>', unsafe_allow_html=True)

    with panel(
        "wahead",
        "How shoppers cope today",
        "Behavioural workarounds invented because the app has no built-in answer.",
        "wrench",
        divider=False,
    ):
        pass

    workarounds = (
        view["workaround"]
        .dropna()
        .apply(lambda x: str(x).strip())
        .loc[lambda x: (x != "") & (~x.str.lower().isin(["none", "null"]))]
        .value_counts()
        .head(9)
    )

    if workarounds.empty:
        st.info("No workarounds recorded in this slice.")
    else:
        w_cols = st.columns(3, gap="medium")
        for i, (wa_text, wa_count) in enumerate(workarounds.items()):
            with w_cols[i % 3]:
                st.markdown(
                    f'<div class="wa-card"><div class="txt">"{html.escape(wa_text)}"</div>'
                    f'<div class="cnt">Mentioned {wa_count:,} times</div></div>',
                    unsafe_allow_html=True,
                )


# ==================================================================
# 5. HOW IT WORKS
# ==================================================================
if nav == "How it works":
    guide("Try the classifier on your own text, then read how the corpus was built.")

    with panel(
        "extractor",
        "Live extractor",
        "Run the classification prompt on any raw review. The result is written to the dataset and every chart refreshes.",
        "flask",
    ):
        sample_text = (
            "I have like 40 things in my Myntra wishlist. There's this one kurta "
            "I've been eyeing for two months but I'm a size M in some brands and L "
            "in others so I keep putting it off. Ended up checking Amazon to see if "
            "the same brand had a size guide there."
        )

        input_text = st.text_area("Customer review or conversation", value=sample_text)
        run_extract = st.button("Run extraction", type="primary", icon=":material/play_arrow:")

    if run_extract:
        with st.spinner("Classifying with the LLM router…"):
            try:
                import csv

                from extract import FIELDNAMES, build_system_prompt
                from llm import LLMRouter, parse_json_response

                router = LLMRouter(verbose=False)
                raw_response, provider = router.complete(build_system_prompt(), f"[1] {input_text}", max_tokens=1500)
                extracted_json = parse_json_response(raw_response)[0]

                new_id = str(uuid.uuid4())
                record = {
                    "id": new_id,
                    "source": "live_demo",
                    "url": "https://live.demo/user-input",
                    "text": input_text[:500],
                    "relevant": extracted_json.get("relevant"),
                    "save_motive": extracted_json.get("save_motive"),
                    "current_blocker": extracted_json.get("current_blocker"),
                    "uncertainty_type": extracted_json.get("uncertainty_type"),
                    "external_channel": extracted_json.get("external_channel"),
                    "workaround": extracted_json.get("workaround"),
                    "segment_gender": extracted_json.get("segment_gender"),
                    "segment_category": extracted_json.get("segment_category"),
                    "segment_price_tier": extracted_json.get("segment_price_tier"),
                    "segment_occasion": extracted_json.get("segment_occasion"),
                    "severity": extracted_json.get("severity"),
                    "evidence_quote": extracted_json.get("evidence_quote"),
                    "confidence": extracted_json.get("confidence"),
                    "provider": provider,
                }

                # Write against the file's ACTUAL header, not a hardcoded list.
                # The two drift apart - the audit added provenance columns and
                # extract.py added signal_type - and DictWriter would then append
                # a row whose values land in the wrong columns, silently
                # corrupting the corpus rather than failing.
                if os.path.exists(DATA_PATH):
                    with open(DATA_PATH, newline="", encoding="utf-8") as f:
                        header = next(csv.reader(f), list(FIELDNAMES))
                else:
                    header = list(FIELDNAMES)

                unknown = [k for k in record if k not in header]
                if unknown:
                    st.warning(
                        "These fields have no column in `data/extracted.csv` and were not saved: "
                        + ", ".join(f"`{k}`" for k in unknown)
                    )

                write_header = not os.path.exists(DATA_PATH)
                with open(DATA_PATH, "a", newline="", encoding="utf-8") as f:
                    writer = csv.DictWriter(f, fieldnames=header, extrasaction="ignore")
                    if write_header:
                        writer.writeheader()
                    writer.writerow({k: record.get(k, "") for k in header})
                    f.flush()

                st.cache_data.clear()

                with panel("extractout", "Extraction result", f"Written to `data/extracted.csv` as record `{new_id[:8]}`.", "check"):
                    st.success(f"Extracted by {provider}. All charts and metrics now include it.")

                    if not extracted_json.get("relevant"):
                        st.warning(
                            "Classified as **not relevant** to wishlist decision-making. Reviews about "
                            "logistics, app bugs or generic praise count towards the total but are "
                            "excluded from the blocker charts."
                        )
                    else:
                        d1, d2, d3 = st.columns(3, gap="medium")
                        with d1:
                            stat("Save motive", bucket_label(extracted_json.get("save_motive", "—")), icon_name="bookmark")
                        with d2:
                            stat("Current blocker", bucket_label(extracted_json.get("current_blocker", "—")), icon_name="alert")
                        with d3:
                            stat("Severity", str(extracted_json.get("severity", "—")).capitalize(), icon_name="trend")

                    # The remaining fields, read as a table rather than raw JSON.
                    # "n" is the model's internal batch index and means nothing here.
                    def _val(key):
                        v = extracted_json.get(key)
                        if v is None or str(v).strip().lower() in ("", "none", "null", "nan", "unclear"):
                            return None
                        return str(v)

                    quote = _val("evidence_quote")
                    if quote:
                        st.markdown('<div class="spacer-md"></div>', unsafe_allow_html=True)
                        st.markdown(
                            f'<div class="extract-quote">{icon("quote", 15, BRAND_INK)}'
                            f"<span>{html.escape(quote)}</span></div>",
                            unsafe_allow_html=True,
                        )

                    detail = [
                        ("Uncertainty", bucket_label(_val("uncertainty_type")) if _val("uncertainty_type") else None),
                        ("Went to", _val("external_channel").title() if _val("external_channel") else None),
                        ("Workaround", _val("workaround")),
                        ("Shopper", _val("segment_gender")),
                        ("Category", _val("segment_category")),
                        ("Price tier", _val("segment_price_tier")),
                        ("Occasion", _val("segment_occasion")),
                        ("Confidence", _val("confidence").capitalize() if _val("confidence") else None),
                    ]
                    shown = [(k, v) for k, v in detail if v]
                    if shown:
                        st.markdown('<div class="spacer-sm"></div>', unsafe_allow_html=True)
                        st.markdown(
                            '<div class="extract-grid">'
                            + "".join(
                                f'<div class="cell"><span class="k">{html.escape(k)}</span>'
                                f'<span class="v">{html.escape(v)}</span></div>'
                                for k, v in shown
                            )
                            + "</div>",
                            unsafe_allow_html=True,
                        )
                    blank = [k for k, v in detail if not v]
                    if blank:
                        st.caption("Not stated in the text: " + ", ".join(blank).lower() + ".")

                    with st.expander("Raw model output"):
                        st.json({k: v for k, v in extracted_json.items() if k != "n"})

            except Exception as ex:
                st.error(f"Extraction failed: {ex}")

    with panel("method", "Methodology", "How the corpus was collected, classified and scored.", "compass"):
        st.markdown(
            """
##### 1 · Multi-channel data harvesting
- **Google Play** — long-form reviews via `google-play-scraper`; reviews under 25 characters are dropped.
- **Apple App Store** — 23 storefronts, to reach the diaspora and premium fashion demographics Apple's India feed alone misses. Apple's RSS feed is a rolling window, so archived pulls are kept and merged rather than replaced.
- **YouTube** — comments on unboxing, try-on haul and comparison videos via the YouTube Data API.

##### 2 · AI structured extraction
- **Router** — Gemini `3.5-flash-lite`, with Groq `gpt-oss-120b` as fallback. The lighter Gemini model was chosen on measured accuracy, not just cost: the reasoning models spent thousands of thinking tokens on a classification task and still missed short, blunt, emoji-heavy complaints that the lite model caught.
- **No keyword bias** — every item is classified without pre-filtering on the word "wishlist", so the sample is not selected on the outcome being measured.
- **Taxonomy disentanglement** — **save motive** (why it was added) is decoupled from **current blocker** (what prevents purchase now). The two are frequently different, and conflating them is what makes most wishlist analysis misleading.
- **Key folding** — the model sometimes returns the short alias for a bucket (`price` instead of `price_waiting`). Aliases are folded into their canonical bucket on load, so one blocker never appears as two rows with the same name.

##### 2b · Corpus rebuild
The whole corpus was re-collected and re-classified end to end, because the first
pass had four failure modes that silently dropped rows: an unparseable-JSON batch
was skipped rather than retried, the fallback provider's model id had been retired
and 404'd, a hardcoded field list wrote columns out of alignment against a changed
header, and an 8,000-token response cap truncated long batches. All four are fixed
and the run is resumable per shard.

- **Model** — every row was classified by a single model on a single prompt, so no
  part of the corpus is judged more or less strictly than another.
- **Deduplication on two axes** — by stable id, and by normalised text (case,
  whitespace, punctuation and emoji stripped). Apple issues a different review id
  per storefront, so the same reviewer can otherwise appear several times.
- **Nothing is dropped for being inconvenient.** Signals that fit no bucket stay in
  `other`, and that share is shown rather than hidden.

##### 2c · Scoring against the business metric
The metric is **the percentage of users who buy at least one saved item within 30 days**. Three properties of it decide what a blocker actually costs, and raw frequency captures none of them:
- **Users, not items.** One shopper complaining ten times is still one user.
- **At least *one*.** A doubt about a single product is survivable — the shopper buys something else in the list. A doubt about Myntra itself blocks every saved item at once. Each signal is tagged `item` or `platform` for exactly this.
- **Within 30 days.** "Waiting for the Diwali sale" is a real purchase that lands outside the window. Each signal is tagged for whether it can plausibly close inside it.

Both tags are assigned per signal by `scripts/scope_tag.py`. They are estimated on **YouTube comments only**: an app reviewer writes "always out of stock" where a shopper looking at one garment writes "sold out in M", and pooling the two put `out_of_stock` at 87% wishlist-wide on app reviews against 30% on YouTube. The ordering is unchanged by that control — quality stays far more wishlist-wide than fit — but the level is, which is what a venue artifact looks like.

Buckets whose 95% confidence intervals overlap **share a rank** rather than being printed 1, 2, 3. At n≈1,500 the top three are not separable, and presenting them as ordered would be the easiest way to mislead someone skimming.

##### 3 · Opportunity scoring
"""
        )
        st.markdown("$$Score = \\text{Blocker frequency (\\%)} \\times \\text{Average severity (1–3)} \\times \\text{Coverage gap}$$")
        st.markdown(
            "Coverage gap is a manual 0–1 estimate of how poorly the current product serves that blocker, "
            "so a frequent-but-well-served problem ranks below a rarer one with no existing solution."
        )
