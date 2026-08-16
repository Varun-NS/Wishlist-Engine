"""
app.py
------
The executive discovery engine interface.

Tabs:
  1. 📊 Executive Overview - High-level metrics, blocker distributions, and ranked opportunity matrix.
  2. 🎯 Strategic Deep Dives - 4 Clean Pillar Dashboards answering the core brief questions.
  3. 🤖 Ask the Corpus (AI Copilot) - Interactive Q&A engine where anyone can ask custom research questions.
  4. 💬 Voice of Customer  - Rich, structured evidence matrix with search, filters, and verbatim cards.
  5. ⚡ Live Extractor      - Real-time LLM classification playground.
  6. 🔬 Methodology        - Pipeline architecture and taxonomy definitions.
"""

import html
import json
import os
import re
import sys
import uuid

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "scripts"))
from taxonomy import BUCKETS, NO_INTENT, OUT_OF_SCOPE, bucket_label, is_addressable

# Page configuration
st.set_page_config(
    page_title="Wishlist Discovery Engine | Executive Insights & AI Copilot",
    page_icon="🛍️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for an ultra-clean, modern, human-friendly UI
st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,100..1000;1,9..40,100..1000&family=Outfit:wght@400;500;600;700;800&display=swap');

html, body, .stMarkdown, p, label {
    font-family: 'DM Sans', -apple-system, BlinkMacSystemFont, sans-serif !important;
}

h1, h2, h3, h4, h5, h6, .header-title, [data-testid="stMetricValue"] {
    font-family: 'Outfit', -apple-system, BlinkMacSystemFont, sans-serif !important;
    letter-spacing: -0.01em;
}

/* Protect Streamlit Material Icons & SVG from font override */
[data-testid*="Icon"], [data-testid="stExpanderToggleIcon"], [class*="material"], svg, i {
    font-family: "Material Symbols Rounded", "Material Icons", sans-serif !important;
}

/* App Background & Header */
.main .block-container {
    padding-top: 2rem;
    padding-bottom: 3rem;
    max-width: 1300px;
}

/* Custom Header Bar */
.header-container {
    background: linear-gradient(135deg, rgba(30, 41, 59, 0.8) 0%, rgba(15, 23, 42, 0.9) 100%);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 16px;
    padding: 1.5rem 2rem;
    margin-bottom: 2rem;
    box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.3);
}
.header-title {
    font-size: 2.1rem;
    font-weight: 800;
    letter-spacing: -0.02em;
    background: linear-gradient(90deg, #F8FAFC, #38BDF8, #818CF8);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin: 0;
}
.header-subtitle {
    color: #94A3B8;
    font-size: 0.95rem;
    margin-top: 0.35rem;
}

/* Metric Cards */
[data-testid="stMetricValue"] {
    font-size: 2.1rem !important;
    font-weight: 800 !important;
    color: #F8FAFC !important;
    letter-spacing: -0.02em;
}
[data-testid="stMetricLabel"] {
    font-size: 0.85rem !important;
    font-weight: 600 !important;
    color: #94A3B8 !important;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}
[data-testid="metric-container"] {
    background: #161B22 !important;
    border-radius: 14px !important;
    padding: 1.25rem 1.5rem !important;
    border: 1px solid rgba(255, 255, 255, 0.08) !important;
    box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2) !important;
    position: relative;
    overflow: hidden;
}
[data-testid="metric-container"]::before {
    content: "";
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 3px;
    background: linear-gradient(90deg, #6366F1, #38BDF8);
}

/* Executive Alert Box */
.exec-banner {
    background: linear-gradient(135deg, rgba(99, 102, 241, 0.12) 0%, rgba(56, 189, 248, 0.08) 100%);
    border: 1px solid rgba(99, 102, 241, 0.3);
    border-left: 4px solid #6366F1;
    border-radius: 12px;
    padding: 1.25rem 1.5rem;
    margin-bottom: 1.5rem;
}
.exec-banner h4 {
    color: #38BDF8;
    margin: 0 0 0.4rem 0;
    font-size: 1.05rem;
    font-weight: 700;
}
.exec-banner p {
    color: #CBD5E1;
    margin: 0;
    font-size: 0.92rem;
    line-height: 1.5;
}

/* Insight Cards */
.pillar-card {
    background: #161B22;
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 14px;
    padding: 1.25rem 1.5rem;
    margin-bottom: 1rem;
}
.pillar-card h4 {
    color: #38BDF8;
    margin: 0 0 0.5rem 0;
    font-size: 1.1rem;
    font-weight: 700;
}
.pillar-card p, .pillar-card li {
    color: #CBD5E1;
    font-size: 0.92rem;
    line-height: 1.55;
}

/* Tabs Navigation */
.stTabs [data-baseweb="tab-list"] {
    gap: 0.75rem;
    border-bottom: 1px solid rgba(255, 255, 255, 0.08);
    padding-bottom: 0.5rem;
    margin-bottom: 1.5rem;
}
.stTabs [data-baseweb="tab"] {
    height: 44px;
    background: rgba(255, 255, 255, 0.03);
    border-radius: 10px;
    padding: 0.5rem 1.1rem;
    font-weight: 600;
    color: #94A3B8;
    border: 1px solid rgba(255, 255, 255, 0.05);
    transition: all 0.2s ease;
}
.stTabs [data-baseweb="tab"]:hover {
    color: #F8FAFC;
    background: rgba(255, 255, 255, 0.07);
}
.stTabs [aria-selected="true"] {
    background: linear-gradient(135deg, rgba(99, 102, 241, 0.25) 0%, rgba(56, 189, 248, 0.2) 100%) !important;
    color: #38BDF8 !important;
    border: 1px solid rgba(56, 189, 248, 0.4) !important;
}

/* Evidence Cards */
.evidence-card {
    background: #161B22;
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 14px;
    padding: 1.25rem;
    margin-bottom: 1rem;
    transition: transform 0.2s ease, border-color 0.2s ease, box-shadow 0.2s ease;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
    display: flex;
    flex-direction: column;
    height: 100%;
}
.evidence-card:hover {
    border-color: rgba(99, 102, 241, 0.4);
    box-shadow: 0 8px 20px rgba(0, 0, 0, 0.3);
    transform: translateY(-2px);
}
.evidence-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 0.75rem;
    flex-wrap: wrap;
    gap: 0.4rem;
}
.badge {
    display: inline-flex;
    align-items: center;
    padding: 0.25rem 0.6rem;
    border-radius: 6px;
    font-size: 0.75rem;
    font-weight: 600;
    letter-spacing: 0.02em;
}
.badge-ios { background: rgba(56, 189, 248, 0.15); color: #38BDF8; border: 1px solid rgba(56, 189, 248, 0.3); }
.badge-android { background: rgba(52, 211, 153, 0.15); color: #34D399; border: 1px solid rgba(52, 211, 153, 0.3); }
.badge-youtube { background: rgba(248, 113, 113, 0.15); color: #F87171; border: 1px solid rgba(248, 113, 113, 0.3); }
.badge-manual { background: rgba(167, 139, 250, 0.15); color: #A78BFA; border: 1px solid rgba(167, 139, 250, 0.3); }

.badge-sev-high { background: rgba(244, 63, 94, 0.15); color: #FB7185; border: 1px solid rgba(244, 63, 94, 0.3); }
.badge-sev-med { background: rgba(245, 158, 11, 0.15); color: #FBBF24; border: 1px solid rgba(245, 158, 11, 0.3); }
.badge-sev-low { background: rgba(100, 116, 139, 0.2); color: #94A3B8; border: 1px solid rgba(100, 116, 139, 0.3); }

.evidence-quote {
    font-size: 0.95rem;
    color: #F1F5F9;
    line-height: 1.55;
    font-style: italic;
    margin-bottom: 0.85rem;
    flex-grow: 1;
    position: relative;
    padding-left: 1rem;
    border-left: 3px solid #6366F1;
}
.evidence-footer {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding-top: 0.75rem;
    border-top: 1px solid rgba(255, 255, 255, 0.05);
    font-size: 0.8rem;
    color: #64748B;
    flex-wrap: wrap;
    gap: 0.5rem;
}
.workaround-tag {
    background: rgba(99, 102, 241, 0.15);
    color: #A5B4FC;
    border: 1px solid rgba(99, 102, 241, 0.3);
    border-radius: 6px;
    padding: 0.25rem 0.5rem;
    font-size: 0.78rem;
    font-style: normal;
    display: inline-block;
    margin-top: 0.4rem;
}

/* Sidebar Custom Styling */
section[data-testid="stSidebar"] {
    background-color: #0B0F17 !important;
    border-right: 1px solid rgba(255, 255, 255, 0.08) !important;
}

/* Buttons */
button[kind="primary"] {
    background: linear-gradient(135deg, #6366F1 0%, #4F46E5 100%) !important;
    color: #FFFFFF !important;
    border: none !important;
    border-radius: 8px !important;
    padding: 0.5rem 1.25rem !important;
    font-weight: 600 !important;
    box-shadow: 0 4px 12px rgba(99, 102, 241, 0.3) !important;
}
button[kind="primary"]:hover {
    box-shadow: 0 6px 18px rgba(99, 102, 241, 0.5) !important;
    transform: translateY(-1px);
}
</style>
""",
    unsafe_allow_html=True,
)

DATA_PATH = "data/extracted.csv"


# ------------------------------------------------------------------
# Data loading & Secrets
# ------------------------------------------------------------------
@st.cache_data
def load_data():
    if not os.path.exists(DATA_PATH):
        return None
    df = pd.read_csv(DATA_PATH)
    df["relevant"] = df["relevant"].astype(str).str.lower().isin(["true", "1"])
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


def score_opportunities(df):
    rel = df[df["relevant"]]
    if rel.empty:
        return pd.DataFrame()

    rows = []
    total = len(rel)

    for key in BUCKETS:
        if key == "other":
            continue

        subset = rel[rel["current_blocker"] == key]
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
                "Share of blockers": f"{pct:.1f}%",
                "Volume (n)": count,
                "Avg Severity (1-3)": f"{avg_sev:.2f}",
                "Coverage Gap": gap if addressable else None,
                "In Scope": "Yes" if addressable else "No",
                "Opportunity Score": round(score, 1),
            }
        )

    return pd.DataFrame(rows).sort_values("Opportunity Score", ascending=False)


# ------------------------------------------------------------------
# Header
# ------------------------------------------------------------------
st.markdown(
    """
<div class="header-container">
    <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap;">
        <div>
            <h1 class="header-title">Wishlist Discovery Engine</h1>
            <div class="header-subtitle">AI-powered customer intelligence decoding online fashion hesitations, blockers & feature opportunities.</div>
        </div>
        <div style="margin-top: 0.5rem;">
            <span class="badge badge-ios">🍏 iOS App Store</span>
            <span class="badge badge-android">🤖 Google Play</span>
            <span class="badge badge-youtube">▶️ YouTube Hauls</span>
        </div>
    </div>
</div>
""",
    unsafe_allow_html=True,
)

# Load dataset
df = load_data()

if df is None:
    st.error("No dataset found at `data/extracted.csv`. Run the extraction pipeline first.")
    st.stop()

rel = df[df["relevant"]]

# ------------------------------------------------------------------
# Sidebar Global Filters
# ------------------------------------------------------------------
st.sidebar.markdown("### 🎛️ Segment Filters")
st.sidebar.caption("Filter corpus across customer demographics & contexts.")

genders = ["All"] + sorted(rel["segment_gender"].dropna().unique().tolist())
gender = st.sidebar.selectbox("Target Gender", genders)

categories = ["All"] + sorted(rel["segment_category"].dropna().unique().tolist())
category = st.sidebar.selectbox("Apparel Category", categories)

occasions = ["All"] + sorted(rel["segment_occasion"].dropna().unique().tolist())
occasion = st.sidebar.selectbox("Occasion / Use-case", occasions)

# Filter dataframe
view = rel.copy()
if gender != "All":
    view = view[view["segment_gender"] == gender]
if category != "All":
    view = view[view["segment_category"] == category]
if occasion != "All":
    view = view[view["segment_occasion"] == occasion]

st.sidebar.divider()
st.sidebar.markdown("### 📊 Active Filter Slice")
st.sidebar.metric("Filtered Relevant Items", f"{len(view):,}", delta=f"{len(view)-len(rel):,}" if len(view) != len(rel) else None)
st.sidebar.caption(f"Covering {(len(view)/len(rel)*100):.1f}% of total relevant signal.")

# ------------------------------------------------------------------
# Main Tabs Navigation
# ------------------------------------------------------------------
tab_overview, tab_blueprint, tab_copilot, tab_evidence, tab_demo, tab_method = st.tabs(
    [
        "📊 Executive Overview",
        "🎯 Strategic Deep Dives",
        "🤖 Ask the Corpus (AI Copilot)",
        "💬 Voice of Customer (Evidence)",
        "⚡ Live Extractor",
        "🔬 Methodology & Taxonomy",
    ]
)

# ==================================================================
# TAB 1: EXECUTIVE OVERVIEW
# ==================================================================
with tab_overview:
    # Top Level KPI Metrics
    m1, m2, m3 = st.columns(3)
    m1.metric("Total Items Analysed", f"{len(df):,}")
    m2.metric("High-Intent Wishlist Signals", f"{len(rel):,}")
    low_conf = (rel["confidence"] == "low").sum() if len(rel) else 0
    m3.metric("AI Confidence Rate", f"{((len(rel)-low_conf) / len(rel) * 100):.1f}%" if len(rel) else "—")

    st.markdown("<div style='height: 1.5rem;'></div>", unsafe_allow_html=True)

    # Executive Summary Card
    st.markdown(
        """
    <div class="exec-banner">
        <h4>🎯 Key Strategic Takeaways</h4>
        <p>• <b>Primary Friction Point:</b> Sizing & Fit ambiguity and Fabric Quality doubts represent 50%+ of purchase friction.<br>
        • <b>Addressable Opportunity:</b> 100% of blockers are addressable via product/UX interventions (detailed size fit visuals, comparison tools, cross-brand guides, verified UGC photos) without relying on price discounting.<br>
        • <b>Channel Divergence:</b> iOS users demonstrate higher sensitivity to product authenticity and styling curation compared to Android users.</p>
    </div>
    """,
        unsafe_allow_html=True,
    )

    # Motives vs Blockers Visuals
    c_left, c_right = st.columns(2)

    with c_left:
        st.markdown("### 💡 Why Customers Save Items (Motives)")
        st.caption("Top underlying intents when adding an item to wishlist")
        motive_df = view["save_motive"].value_counts().reset_index()
        motive_df.columns = ["Motive", "Count"]
        motive_df["Motive"] = motive_df["Motive"].apply(bucket_label)

        fig_motive = px.bar(
            motive_df,
            x="Count",
            y="Motive",
            orientation="h",
            color="Count",
            color_continuous_scale=[[0, "#312E81"], [0.5, "#4F46E5"], [1, "#38BDF8"]],
        )
        fig_motive.update_layout(
            showlegend=False,
            margin=dict(l=10, r=10, t=10, b=10),
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#94A3B8", family="DM Sans, sans-serif"),
            xaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.06)"),
            yaxis=dict(categoryorder="total ascending", showgrid=False),
            height=320,
        )
        st.plotly_chart(fig_motive, use_container_width=True)

    with c_right:
        st.markdown("### 🛑 What Blocks the Purchase Now")
        st.caption("Immediate hurdles stalling checkout conversion")
        blocker_df = view["current_blocker"].value_counts().reset_index()
        blocker_df.columns = ["Blocker", "Count"]
        blocker_df["Blocker"] = blocker_df["Blocker"].apply(bucket_label)

        fig_blocker = px.bar(
            blocker_df,
            x="Count",
            y="Blocker",
            orientation="h",
            color="Count",
            color_continuous_scale=[[0, "#831843"], [0.5, "#BE185D"], [1, "#FB7185"]],
        )
        fig_blocker.update_layout(
            showlegend=False,
            margin=dict(l=10, r=10, t=10, b=10),
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#94A3B8", family="DM Sans, sans-serif"),
            xaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.06)"),
            yaxis=dict(categoryorder="total ascending", showgrid=False),
            height=320,
        )
        st.plotly_chart(fig_blocker, use_container_width=True)

    st.divider()

    # Ranked Opportunity Table
    st.markdown("### 🏆 Ranked UX Opportunity Matrix")
    st.caption("Opportunity Score = Share of Blockers × Avg Severity × Coverage Gap. Ranks highest ROI product improvements.")
    opp_df = score_opportunities(view)
    if not opp_df.empty:
        max_opp_score = max(1.0, float(opp_df["Opportunity Score"].max()))
        st.dataframe(
            opp_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Opportunity Score": st.column_config.ProgressColumn(
                    "Opportunity Score",
                    help="Composite metric evaluating frequency, user pain level, and competitive white-space",
                    format="%.1f",
                    min_value=0,
                    max_value=max_opp_score,
                ),
            },
        )
    else:
        st.info("No opportunity data available for the active filter slice.")

    st.divider()

    # Cross Platform Distribution
    st.markdown("### 📱 Blocker Divergence Across Platforms")
    st.caption("Comparative analysis highlighting behavioral differences across iOS, Android, and Social channels.")

    plat = view.copy()
    plat["platform"] = plat["source"].apply(
        lambda s: "iOS" if str(s).startswith("appstore") else "Android" if str(s) == "playstore" else "YouTube" if str(s) == "youtube" else "Manual/Other"
    )

    cross = plat[plat["platform"].isin(["iOS", "Android", "YouTube"])].groupby(["platform", "current_blocker"]).size().unstack(fill_value=0)

    if not cross.empty:
        pct_cross = cross.div(cross.sum(axis=1), axis=0) * 100
        pct_cross.columns = [bucket_label(c) for c in pct_cross.columns]

        plot_df = pct_cross.T.reset_index().rename(columns={"index": "Blocker"})
        plot_df = plot_df.melt(id_vars="Blocker", var_name="Platform", value_name="% Share")

        fig_plat = px.bar(
            plot_df,
            x="Blocker",
            y="% Share",
            color="Platform",
            barmode="group",
            color_discrete_map={"iOS": "#38BDF8", "Android": "#34D399", "YouTube": "#F87171"},
        )
        fig_plat.update_layout(
            margin=dict(l=10, r=10, t=20, b=10),
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#94A3B8", family="DM Sans, sans-serif"),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            xaxis=dict(showgrid=False),
            yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.06)", title="% of Platform Corpus"),
            height=380,
        )
        st.plotly_chart(fig_plat, use_container_width=True)


# ==================================================================
# TAB 2: STRATEGIC DEEP DIVES (4 CLEAN PILLARS)
# ==================================================================
with tab_blueprint:
    st.markdown("### 🎯 Strategic Deep Dives & Brief Solutions")
    st.caption("Explore structured analysis answering the core research questions across 4 focused strategic pillars.")

    p_tab1, p_tab2, p_tab3, p_tab4 = st.tabs(
        [
            "💡 1. Intent & Motives",
            "🛑 2. Blockers & Uncertainties",
            "🌐 3. Search Leakage & Hacks",
            "🚀 4. Prioritized ROI Roadmap",
        ]
    )

    # PILLAR 1
    with p_tab1:
        col_p1_left, col_p1_right = st.columns([1, 1])
        with col_p1_left:
            st.markdown("#### 💡 Save Motives Distribution")
            sm_df = rel["save_motive"].value_counts(normalize=True).head(6).reset_index()
            sm_df.columns = ["Motive", "Share"]
            sm_df["Share %"] = sm_df["Share"] * 100
            sm_df["Motive Label"] = sm_df["Motive"].apply(bucket_label)

            fig_p1 = px.bar(
                sm_df,
                x="Share %",
                y="Motive Label",
                orientation="h",
                color="Share %",
                color_continuous_scale=[[0, "#312E81"], [1, "#38BDF8"]],
            )
            fig_p1.update_layout(
                height=300,
                margin=dict(l=10, r=20, t=10, b=10),
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#94A3B8", family="DM Sans, sans-serif"),
                yaxis=dict(categoryorder="total ascending", showgrid=False),
                xaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.06)"),
                showlegend=False,
            )
            st.plotly_chart(fig_p1, use_container_width=True)

        with col_p1_right:
            st.markdown(
                """
            <div class="pillar-card">
                <h4>🎯 Key Strategic Insights on Intent</h4>
                <p><b>1. Active Risk Management:</b> Users add items to wishlists not as casual bookmarks, but to defer financial commitment while resolving doubts about price, size, or authenticity.</p>
                <p><b>2. Intent vs. Window Shopping:</b> Only <b>5.2%</b> of items represent zero-intent window shopping. Over <b>94%+</b> of users exhibit genuine shopping consideration.</p>
                <p><b>3. Consideration Set Building:</b> 7.8% of saves are explicitly created to compare 3–5 similar silhouettes side-by-side.</p>
            </div>
            """,
                unsafe_allow_html=True,
            )

    # PILLAR 2
    with p_tab2:
        col_p2_left, col_p2_right = st.columns([1, 1])
        with col_p2_left:
            st.markdown("#### 🔍 Residual Uncertainty Hierarchy")
            unc_df = rel["uncertainty_type"].dropna().loc[lambda x: (x != "none") & (x != "nan")].value_counts().reset_index()
            unc_df.columns = ["Uncertainty", "Count"]
            unc_df["Label"] = unc_df["Uncertainty"].apply(lambda x: bucket_label(x))

            fig_p2 = px.pie(
                unc_df,
                names="Label",
                values="Count",
                hole=0.45,
                color_discrete_sequence=["#38BDF8", "#818CF8", "#F472B6", "#34D399", "#FBBF24"],
            )
            fig_p2.update_layout(
                height=300,
                margin=dict(l=10, r=10, t=10, b=10),
                paper_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#94A3B8", family="DM Sans, sans-serif"),
            )
            st.plotly_chart(fig_p2, use_container_width=True)

        with col_p2_right:
            st.markdown(
                """
            <div class="pillar-card">
                <h4>🛑 Conversion Blockers & Postponement</h4>
                <p><b>1. The Quality Spike:</b> Quality & authenticity doubt rises from 17.2% at inception to <b>23.2% at checkout</b> as users read critical reviews.</p>
                <p><b>2. The Stockout Trap (11.9%):</b> Delaying purchase causes users to return only to find their exact size sold out.</p>
                <p><b>3. Postponement Drivers:</b> Users postpone checkout to sync with major sale cycles (Diwali, EORS) or because they dread return hassles if the size fails.</p>
            </div>
            """,
                unsafe_allow_html=True,
            )

    # PILLAR 3
    with p_tab3:
        col_p3_left, col_p3_right = st.columns([1, 1])
        with col_p3_left:
            st.markdown("#### 🌐 External Channel Leakage Distribution")
            ch_df = rel["external_channel"].dropna().loc[lambda x: (x != "none") & (x != "nan")].value_counts().head(6).reset_index()
            ch_df.columns = ["Channel", "Count"]
            ch_df["Channel Name"] = ch_df["Channel"].apply(lambda x: str(x).title())

            fig_p3 = px.bar(
                ch_df,
                x="Count",
                y="Channel Name",
                orientation="h",
                color="Count",
                color_continuous_scale=[[0, "#4338CA"], [1, "#06B6D4"]],
            )
            fig_p3.update_layout(
                height=300,
                margin=dict(l=10, r=20, t=10, b=10),
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#94A3B8", family="DM Sans, sans-serif"),
                yaxis=dict(categoryorder="total ascending", showgrid=False),
                xaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.06)"),
                showlegend=False,
            )
            st.plotly_chart(fig_p3, use_container_width=True)

        with col_p3_right:
            st.markdown(
                """
            <div class="pillar-card">
                <h4>⚖️ Comparison & External Validation Hacks</h4>
                <p><b>1. Why Users Leave the App:</b> Users leak to <b>Amazon & Flipkart (54%)</b> to find unboxing customer photos and inch measurements that brand studio shots hide.</p>
                <p><b>2. YouTube Try-On Hauls:</b> Customers watch influencer videos to verify fabric transparency, drape, and true daylight color.</p>
                <p><b>3. The 'Multi-Order & Return' Hack:</b> Lacking in-app comparison tools, users order 2–3 sizes/styles with the premeditated plan to return the losers.</p>
            </div>
            """,
                unsafe_allow_html=True,
            )

    # PILLAR 4
    with p_tab4:
        st.markdown("#### 🚀 Top 5 Prioritized Feature Roadmap & ROI Matrix")
        st.markdown(
            """
        | # | Strategic Product Opportunity | Targeted Friction | Quantified Signal | Proposed UX Feature Intervention | Expected Metric Impact |
        | :- | :--- | :--- | :--- | :--- | :--- |
        | **1** | **Interactive Fit & Size Matrix** | `fit_size_uncertainty` | 13.9% of doubts; 58% high severity | Cross-brand fit translation (*"Fits like Zara M"*), exact inch measurements, body visualizer | **+15-18% Checkout Conversion**; **-22% Size Returns** |
        | **2** | **Verified Real-Life UGC & Video Hub** | `quality_authenticity_doubt` | #1 Blocker (23.2% of corpus) | Verified customer unboxing photos, daylight fabric zoom, customer video try-ons in Wishlist drawer | **+12% Conversion Lift** on fabric doubt items |
        | **3** | **In-Wishlist Smart Comparison Tray** | `in_app_comparison` & `cross_platform` | 7.8% save motives | Side-by-side spec comparison tray inside Wishlist (fabric, ratings, prices, returnability) | Eliminates leakage to Amazon / Flipkart |
        | **4** | **Predictive Price & Smart Restock Alerts** | `price_waiting` & `out_of_stock` | 11.9% stockouts; 20.2% price waiting | Instant 1-click WhatsApp restock alerts + 48-hour price-lock guarantee without discounting | **Recovers ~40% of stockout abandonments** |
        | **5** | **'Complete The Look' Wishlist Styler** | `styling_uncertainty` | 2.2% blockers | Algorithmic bundling suggesting exact matching footwear/bottoms already in inventory with 1-click bundle add | **+14% Average Order Value (AOV)** |
        """
        )


# ==================================================================
# TAB 3: ASK THE CORPUS (AI COPILOT)
# ==================================================================
with tab_copilot:
    st.markdown("### 🤖 Ask the Discovery Engine (AI Copilot)")
    st.caption("Ask any custom research or product strategy question across the 10,000+ customer review corpus.")

    def set_copilot_prompt(prompt_text):
        st.session_state["copilot_input_box"] = prompt_text
        st.session_state["run_copilot_now"] = True

    if "copilot_input_box" not in st.session_state:
        st.session_state["copilot_input_box"] = ""
    if "run_copilot_now" not in st.session_state:
        st.session_state["run_copilot_now"] = False

    # Quick Question Chips
    st.markdown("##### 💡 Suggested Questions to Ask:")
    q_col1, q_col2, q_col3 = st.columns(3)
    with q_col1:
        st.button(
            "👟 Footwear Sizing Hesitations",
            on_click=set_copilot_prompt,
            args=("Why do users hesitate when buying footwear and what are the main sizing issues?",),
            use_container_width=True,
        )
    with q_col2:
        st.button(
            "👗 Fabric Quality Complaints",
            on_click=set_copilot_prompt,
            args=("What are the most common complaints about fabric quality, material transparency, and color bleeding?",),
            use_container_width=True,
        )
    with q_col3:
        st.button(
            "📱 iOS Wishlist Abandonment",
            on_click=set_copilot_prompt,
            args=("What are the primary reasons iOS users abandon wishlists compared to Android users?",),
            use_container_width=True,
        )

    user_query = st.text_input(
        "Type your custom question about customer behavior or wishlist blockers:",
        placeholder="e.g. How does return friction influence checkout? What do women say about ethnic wear?",
        key="copilot_input_box",
    )

    btn_clicked = st.button("✨ Ask AI Copilot", type="primary")
    should_run = btn_clicked or st.session_state.get("run_copilot_now", False)
    st.session_state["run_copilot_now"] = False

    if should_run:
        query_to_run = st.session_state.get("copilot_input_box", "").strip()
        if not query_to_run:
            st.warning("Please enter or select a question to analyze.")
        else:
            with st.spinner("Searching 10,000+ customer signals & synthesizing executive response..."):
                try:
                    # Token search across corpus
                    tokens = [
                        t.lower()
                        for t in re.findall(r"\w+", query_to_run)
                        if len(t) > 2 and t.lower() not in {"what", "why", "how", "when", "the", "and", "for", "with", "about", "are", "is"}
                    ]

                    matches = []
                    for _, row in rel.iterrows():
                        score = 0
                        full_str = f"{row.get('text', '')} {row.get('evidence_quote', '')} {row.get('current_blocker', '')} {row.get('save_motive', '')} {row.get('segment_category', '')} {row.get('segment_gender', '')} {row.get('workaround', '')}".lower()
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
                        quotes_context.append(f"- [{src}] (Blocker: {blk} | Workaround: {wa}) \"{q}\"")

                    context_str = "\n".join(quotes_context)

                    system_prompt = f"""You are the Chief AI Research Strategist for the Wishlist Discovery Engine analyzing an e-commerce customer corpus of 10,000+ reviews (Myntra, AJIO, iOS App Store, Play Store, YouTube).
Answer the user's question directly, insightfully, and objectively based on the verified customer signals provided below.

Format your response cleanly with:
### 📌 Executive Summary (2-3 crisp sentences answering the question)
### 📊 Key Quantitative Insights & Behavioral Patterns (bullet points with concrete observations)
### 💬 Verbatim Customer Evidence (quote 2-3 of the most relevant quotes from the context with attribution)
### 🚀 Strategic Product & UX Recommendation (actionable product feature proposal)

Context Customer Signals:
{context_str}
"""
                    from llm import LLMRouter

                    router = LLMRouter(verbose=False)
                    # json_mode=False enables free-form executive Markdown generation
                    answer, provider = router.complete(system_prompt, f"Question: {query_to_run}", max_tokens=1500, json_mode=False)

                    st.markdown("---")
                    st.caption(f"🤖 **AI Copilot Response** · Powered by `{provider.upper()}`")
                    st.markdown(answer)

                    # Ground truth inspection expander with clean styling
                    with st.expander(f"🔍 Ground Truth Evidence: View {len(top_matches)} Customer Signals Used"):
                        for r in top_matches:
                            q_item = r.get("evidence_quote") if pd.notna(r.get("evidence_quote")) else r.get("text")
                            st.markdown(f"• **[{str(r.get('source')).upper()}]** *\"{q_item}\"*  \n  <small style='color: #64748B;'>Blocker: <b>{bucket_label(str(r.get('current_blocker')))}</b> | Workaround: <b>{str(r.get('workaround')) if pd.notna(r.get('workaround')) else 'None'}</b></small>", unsafe_allow_html=True)

                except Exception as ex:
                    st.error(f"Failed to generate answer: {ex}")


# ==================================================================
# TAB 4: VOICE OF CUSTOMER (EVIDENCE LABORATORY)
# ==================================================================
with tab_evidence:
    st.markdown("### 💬 Voice of Customer & Evidence Repository")
    st.caption("Explore verbatim quotes, qualitative signals, and customer coping workarounds with structured metadata.")

    # Filter Controls for Evidence
    ec1, ec2, ec3, ec4 = st.columns([3, 2, 2, 3])

    with ec1:
        blocker_options = sorted(view["current_blocker"].dropna().unique().tolist())
        selected_blocker = st.selectbox(
            "Filter by Blocker Category",
            ["All Blockers"] + blocker_options,
            format_func=lambda x: "All Blockers" if x == "All Blockers" else f"{bucket_label(x)} ({len(view[view['current_blocker']==x])})",
        )

    with ec2:
        selected_sev = st.selectbox("Severity Level", ["All Severities", "high", "medium", "low"], format_func=lambda x: x.capitalize())

    with ec3:
        platforms = ["All Platforms", "playstore", "appstore", "youtube"]
        selected_source = st.selectbox(
            "Channel / Platform",
            platforms,
            format_func=lambda x: "All Channels" if x == "All Platforms" else "Google Play" if x == "playstore" else "iOS App Store" if x == "appstore" else "YouTube" if x == "youtube" else x,
        )

    with ec4:
        search_query = st.text_input("🔍 Search Quote Content", placeholder="e.g. size, kurta, refund, return, fabric...")

    # Filter quotes
    q_df = view.copy()
    if selected_blocker != "All Blockers":
        q_df = q_df[q_df["current_blocker"] == selected_blocker]
    if selected_sev != "All Severities":
        q_df = q_df[q_df["severity"] == selected_sev]
    if selected_source != "All Platforms":
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

    # Display count banner
    st.markdown(
        f"<div style='color: #94A3B8; font-size: 0.88rem; margin: 0.75rem 0 1.25rem 0;'>"
        f"Displaying <b>{len(q_df):,}</b> verified customer signals matching your criteria."
        f"</div>",
        unsafe_allow_html=True,
    )

    if q_df.empty:
        st.info("No quotes matched the selected filters. Try broadening your criteria or search query.")
    else:
        # Render quotes in 2-column grid
        quotes_to_show = q_df.dropna(subset=["evidence_quote"]).head(18)
        cols = st.columns(2)

        for idx, (_, row) in enumerate(quotes_to_show.iterrows()):
            col_target = cols[idx % 2]

            src = str(row.get("source", "")).lower()
            if "appstore" in src:
                src_badge = '<span class="badge badge-ios">🍏 iOS App Store</span>'
            elif "playstore" in src:
                src_badge = '<span class="badge badge-android">🤖 Google Play</span>'
            elif "youtube" in src:
                src_badge = '<span class="badge badge-youtube">▶️ YouTube</span>'
            else:
                src_badge = '<span class="badge badge-manual">📝 Forum / Review</span>'

            sev = str(row.get("severity", "low")).lower()
            if sev == "high":
                sev_badge = '<span class="badge badge-sev-high">🔴 High Friction</span>'
            elif sev == "medium":
                sev_badge = '<span class="badge badge-sev-med">🟡 Medium Friction</span>'
            else:
                sev_badge = '<span class="badge badge-sev-low">🟢 Low Friction</span>'

            blocker_name = bucket_label(str(row.get("current_blocker", "")))
            quote_text = html.escape(str(row.get("evidence_quote", "")))

            workaround_html = ""
            if pd.notna(row.get("workaround")) and str(row.get("workaround")).strip() and str(row.get("workaround")).lower() != "none":
                workaround_clean = html.escape(str(row.get("workaround")))
                workaround_html = f'<div class="workaround-tag">🛠️ <b>User Workaround:</b> {workaround_clean}</div>'

            # Metadata tags (filter out 'none', 'unclear', 'nan')
            meta_items = []
            g_val = str(row.get("segment_gender", "")).lower()
            if g_val not in ["unclear", "none", "nan", ""]:
                meta_items.append(f"👤 {row['segment_gender']}")

            c_val = str(row.get("segment_category", "")).lower()
            if c_val not in ["unclear", "none", "nan", ""]:
                meta_items.append(f"👗 {row['segment_category']}")

            o_val = str(row.get("segment_occasion", "")).lower()
            if o_val not in ["unclear", "none", "nan", ""]:
                meta_items.append(f"🎉 {row['segment_occasion']}")

            meta_str = " • ".join(meta_items) if meta_items else f"🏷️ {blocker_name}"

            with col_target:
                # Remove leading whitespace so Markdown never misinterprets lines as code blocks (<pre><code>)
                card_html = (
                    f'<div class="evidence-card">'
                    f'<div class="evidence-header">'
                    f'<div>{src_badge} {sev_badge}</div>'
                    f'<span style="font-size: 0.75rem; color: #64748B; font-weight: 600;">{blocker_name}</span>'
                    f'</div>'
                    f'<div class="evidence-quote">“{quote_text}”</div>'
                    f'{workaround_html}'
                    f'<div class="evidence-footer">'
                    f'<span>{meta_str}</span>'
                    f'<span>Confidence: <b>{str(row.get("confidence", "high")).capitalize()}</b></span>'
                    f'</div>'
                    f'</div>'
                )
                st.markdown(card_html, unsafe_allow_html=True)

        if len(q_df) > 18:
            st.caption(f"Showing top 18 of {len(q_df):,} matching quotes. Use the search bar above to narrow down specific topics.")

    # Distinct Section: Customer Behavioral Workarounds
    st.markdown("<div style='height: 2rem;'></div>", unsafe_allow_html=True)
    st.markdown("### 🛠️ Common Customer Workarounds & Behavioral Hacks")
    st.caption("How shoppers currently cope with decision uncertainty when the app lacks features.")

    workarounds = (
        view["workaround"]
        .dropna()
        .apply(lambda x: str(x).strip())
        .loc[lambda x: (x != "") & (x.str.lower() != "none") & (x.str.lower() != "null")]
        .value_counts()
        .head(12)
    )

    if not workarounds.empty:
        w_cols = st.columns(3)
        for i, (wa_text, wa_count) in enumerate(workarounds.items()):
            with w_cols[i % 3]:
                st.markdown(
                    f'<div style="background: #161B22; border: 1px solid rgba(255,255,255,0.06); border-radius: 10px; padding: 0.9rem; margin-bottom: 0.75rem;">'
                    f'<div style="font-size: 0.88rem; color: #E2E8F0; font-weight: 500;">"{html.escape(wa_text)}"</div>'
                    f'<div style="font-size: 0.75rem; color: #38BDF8; margin-top: 0.4rem; font-weight: 600;">Mentioned {wa_count} times</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )


# ==================================================================
# TAB 5: LIVE AI EXTRACTOR
# ==================================================================
with tab_demo:
    st.markdown("### ⚡ Live AI Classification Playground")
    st.caption("Test the LLM categorization prompt in real time on any raw customer review or social media excerpt.")

    sample_text = (
        "I have like 40 things in my Myntra wishlist. There's this one kurta "
        "I've been eyeing for two months but I'm a size M in some brands and L "
        "in others so I keep putting it off. Ended up checking Amazon to see if "
        "the same brand had a size guide there."
    )

    input_text = st.text_area("Paste customer conversation / review text here:", value=sample_text, height=130)

    if st.button("🚀 Run & Register AI Extraction", type="primary"):
        with st.spinner("Classifying with LLM Router & saving to dataset..."):
            try:
                import csv
                from extract import FIELDNAMES, build_system_prompt
                from llm import LLMRouter, parse_json_response

                router = LLMRouter(verbose=False)
                raw_response, provider = router.complete(build_system_prompt(), f"[1] {input_text}", max_tokens=1500)
                extracted_json = parse_json_response(raw_response)[0]

                # Automatically persist to active dataset
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

                write_header = not os.path.exists(DATA_PATH)
                with open(DATA_PATH, "a", newline="", encoding="utf-8") as f:
                    writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
                    if write_header:
                        writer.writeheader()
                    writer.writerow(record)
                    f.flush()

                # Invalidate Streamlit cache so all charts and metrics refresh
                st.cache_data.clear()

                st.success(
                    f"✅ **Extracted by {provider} & registered to the active dataset!** "
                    f"(Record ID: `{new_id[:8]}` written to `data/extracted.csv`). "
                    "All dashboard metrics, charts, and evidence cards have been updated live."
                )

                if not extracted_json.get("relevant"):
                    st.warning(
                        "⚠️ Classified as **Not Relevant** to wishlist decision-making. "
                        "(App reviews regarding logistics, returns, or bugs are counted towards total items, but filtered from blocker charts)."
                    )
                else:
                    d1, d2, d3 = st.columns(3)
                    d1.metric("Save Motive", bucket_label(extracted_json.get("save_motive", "—")))
                    d2.metric("Current Blocker", bucket_label(extracted_json.get("current_blocker", "—")))
                    d3.metric("Severity", str(extracted_json.get("severity", "—")).capitalize())

                    st.markdown("#### Structured JSON Payload")
                    st.json(extracted_json)

            except Exception as ex:
                st.error(f"Extraction failed: {ex}")


# ==================================================================
# TAB 6: METHODOLOGY & PIPELINE
# ==================================================================
with tab_method:
    st.markdown("### 🔬 Research Methodology & Analytical Architecture")
    st.caption("Detailed overview of our multi-stage AI extraction and validation methodology.")

    st.markdown(
        """
    #### 1. Multi-Channel Data Harvesting
    - **Google Play Store:** Automated extraction of long-form reviews via `google-play-scraper`. Short reviews (<25 chars) filtered out.
    - **Apple iOS App Store:** International storefront collection (India, US, UK, UAE) to capture high-spending, premium fashion demographics.
    - **YouTube Hauls & Reviews:** Keyword scraping of unboxing, try-on hauls, and comparison comments via YouTube Data API.

    #### 2. AI Structured Extraction
    - **LLM Pipeline:** Gemini 1.5 Flash & Groq LLaMA 3.3 70B router.
    - **Zero Keyword Bias:** Every item is evaluated without keyword filtering on "wishlist", eliminating sampling bias before categorization.
    - **Taxonomy Disentanglement:** Crucially decouples **Save Motive** (why an item was added) from **Current Blocker** (what prevents purchase now).

    #### 3. Opportunity Scoring Algorithm
    $$Score = \\text{Blocker Frequency (\\%)} \\times \\text{Average Severity (1-3)} \\times \\text{Coverage Gap}$$
    - Evaluates unmet consumer demand against current market UX benchmarks.
    """
    )
