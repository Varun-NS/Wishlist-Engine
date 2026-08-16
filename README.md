# 🛍️ Wishlist Discovery Engine — E-Commerce Customer Intelligence

An enterprise-grade AI research engine that ingests, categorizes, and quantifies **10,180+ real-world customer signals** across Google Play, Apple App Store, and YouTube to uncover what prevents wishlisted fashion products from converting to purchases on Myntra.

---

## 🎯 Key Strategic Insights at a Glance

* **10,180 Customer Signals Analyzed:** 5,846 Google Play Store reviews, 3,643 iOS App Store reviews (across 8 international storefronts), and 692 YouTube try-on haul comments.
* **100% Addressable Opportunities:** Sizing uncertainty (13.9%) and Fabric/Quality doubts (23.2%) are fully addressable through UX/product interventions without requiring price discounting.
* **Cross-Channel Behavior:** iOS users demonstrate higher sensitivity to product authenticity and styling curation compared to Android users.
* **Hybrid Intelligence Architecture:** Offline batch LLM schema extraction paired with an **In-Memory RAG Copilot** for instant qualitative and quantitative strategy synthesis.

---

## 🖥️ Live Dashboard Architecture (5 Tabs)

```
Wishlist Discovery Engine
├── Overview          The answer in one screen: headline finding, 4 KPI tiles,
│                     motives vs. blockers, ranked opportunity matrix,
│                     platform divergence (collapsed by default)
├── Deep dives        4 strategic pillars behind one pill selector:
│                     intent, blockers & uncertainty, search leakage, ROI roadmap
├── AI copilot        Ask the corpus — in-memory retrieval, 1-click starter
│                     questions, ground-truth citations for every answer
├── Voice of customer Evidence grid with blocker / severity / channel filters,
│                     full-text search, and the workarounds shoppers invented
└── How it works      Live extractor playground + methodology
```

### Design system

| Layer | Choice |
| :--- | :--- |
| Surface | Apple-style frosted glass panels — 74% white, 30px backdrop blur, 180% saturation, 22px radius, over a soft rose/blue/amber gradient field. Opacity is deliberately high: Apple's own materials are near-opaque, and that is what keeps text legible on glass |
| Structure | Every section is its own titled panel with an icon chip, a name and a one-line description, so the page reads as discrete parts rather than a continuous wall |
| Navigation | A session-state-driven segmented control, **not `st.tabs`** — a tab's selection lives in the component's client-side state, and a rerun triggered from inside a tab can remount it and throw the user back to the first tab. Driving it from session state makes the selection survive every rerun, and each section is deep-linkable as `?view=overview\|deep-dives\|copilot\|voice\|method` |
| Palette | Myntra light — rose `#FF3F6C` accent, ink `#1C1E2E`, muted `#5C6076` |
| Type | Outfit (headings) + DM Sans (body) on a **17px base** with 1.7 line-height; hierarchy carried by weight and size, not colour |
| Icons | Material Symbols and inline SVG — no emoji used as an icon |
| Store marks | The App Store, Google Play and YouTube marks label every signal with its source, in the header chips and on each evidence card. Inline SVG so the app stays self-contained offline, never recoloured or re-proportioned. They are **reconstructions**: drop the official asset in as `assets/app-store.svg`, `assets/google-play.svg` or `assets/youtube.svg` and it is used instead, no code change. Trademarks of Apple Inc. and Google LLC, used to attribute the data source |
| Charts | Single-hue magnitude bars with direct value labels. Platform identity uses a validated 3-hue set (`#2563A8` / `#0F8A6E` / `#B26B00`) that clears WCAG contrast and colour-vision-deficiency separation thresholds |

Every text/background pair was measured against the *composited* glass surface
rather than a nominal hex: the smallest labels land at 5.4–6.0:1 and body copy at
11.5:1, all clear of WCAG AA. `prefers-contrast: more` drops the blur for solid
white panels, and `prefers-reduced-motion` disables every transition.

### How buckets are counted

Nothing is dropped. Alias keys the extractor emits (`price` vs. `price_waiting`)
are canonicalised on load so one blocker cannot appear as two identically-named
rows. The Overview charts show **every** named bucket, however small. The
taxonomy's residuals — `other` (no bucket fit) and `none` (no blocker stated) —
are folded into a single **Other / unspecified** row that always sorts last and
never leads a ranking or the headline, and the Overview tab has a dedicated panel
breaking that row back out into its exact parts and percentages.

---

## 🚀 Quickstart & Setup

### 1. Prerequisites
Ensure you have **Python 3.9+** installed:
```bash
python3 --version
```

### 2. Clone & Setup Virtual Environment
```bash
git clone https://github.com/Varun-NS/Wishlist-Engine.git
cd Wishlist-Engine

python3 -m venv venv
source venv/bin/activate    # Mac / Linux
# venv\Scripts\activate     # Windows
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables
Create a `.env` file in the root directory:
```bash
GEMINI_API_KEY="your_gemini_api_key"
GROQ_API_KEY="your_groq_api_key"
YOUTUBE_API_KEY="your_youtube_api_key"  # Optional, for running YouTube scraper
```

### 5. Launch the Streamlit Dashboard
```bash
streamlit run app.py
```
Open **`http://localhost:8501`** in your browser.

---

## 🧠 Research & Extraction Pipeline

```
Collect (10,180 items) ➔ Extract (LLM Router) ➔ Decouple Taxonomy ➔ Quantify & Rank ➔ Interactive Copilot
```

### Step 1: Multi-Channel Data Harvesting
```bash
python scripts/collect_playstore.py   # Scrapes 5,800+ long-form Google Play reviews
python scripts/collect_appstore.py    # Scrapes 3,600+ iOS reviews across 8 country storefronts
python scripts/collect_youtube.py     # Scrapes 690+ comments on Myntra try-on hauls & reviews
python scripts/collect_manual.py      # Structured template for Reddit/forum qualitative inputs
```

### Step 2: AI Structured Batch Extraction
Processes raw text with an automatic **Gemini 2.5 Flash ➔ Groq LLaMA 3.3 70B fallback router**:
```bash
python scripts/extract.py
```
Outputs: `data/extracted.csv` with 18 structured columns (save motives, blockers, uncertainties, severity, external channels, workarounds, personas).

### Step 3: Opportunity Scoring Algorithm
$$\text{Opportunity Score} = \text{Blocker Frequency (\%)} \times \text{Average Severity (1--3)} \times \text{Coverage Gap}$$

---

## ☁️ Deployment Guide (Streamlit Community Cloud)

1. Fork or push this repository to your GitHub: **`Varun-NS/Wishlist-Engine`**.
2. Visit **[share.streamlit.io](https://share.streamlit.io/)** and click **New App**.
3. Select your repository, set the branch to `main`, and main file to `app.py` (or `streamlit_app.py`).
4. In **Advanced Settings ➔ Secrets**, add:
   ```toml
   GEMINI_API_KEY = "your_gemini_key"
   GROQ_API_KEY = "your_groq_key"
   ```
5. Click **Deploy!**

---

## 📂 Repository Structure

```
Wishlist-Engine/
├── app.py                      # Main Streamlit Dashboard (Myntra theme, Plotly, Copilot)
├── streamlit_app.py            # Entrypoint alias for Streamlit Cloud
├── requirements.txt            # Production runtime dependencies
├── .streamlit/
│   └── config.toml             # Myntra brand light palette configuration
├── data/
│   ├── extracted.csv           # 10,180 structured customer signals (committed)
│   └── raw_*.csv               # Scraped source files (gitignored)
└── scripts/
    ├── taxonomy.py             # Taxonomy definitions, aliases & addressability rules
    ├── llm.py                  # Dual-provider LLM router with JSON & Markdown modes
    ├── extract.py              # Batch AI extraction pipeline
    ├── collect_playstore.py    # Google Play Store harvester
    ├── collect_appstore.py     # Apple App Store international harvester
    ├── collect_youtube.py      # YouTube try-on haul comments harvester
    ├── collect_manual.py       # Manual qualitative input pipeline
    └── validate.py             # Human-AI agreement validation script
```

---

## 🛡️ Privacy & Security
* `.env` is strictly `.gitignore`d. No API keys, credentials, or private credentials are included in the repository.
* All data is processed using anonymized public reviews and user comments.
