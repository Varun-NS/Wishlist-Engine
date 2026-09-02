# 🛍️ Wishlist Discovery Engine — E-Commerce Customer Intelligence

An enterprise-grade AI research engine that ingests, categorizes, and quantifies **15,661 real-world customer signals** across Google Play, Apple App Store, and YouTube to uncover what prevents wishlisted fashion products from converting to purchases on Myntra.

---

## 🎯 The business metric

> **Increase the percentage of users who purchase at least one item from their wishlist within 30 days of adding it.**

Everything in the app is ranked against that sentence, not against complaint volume. Three properties of it change the answer:

| Property | Why it changes the ranking |
| :--- | :--- |
| **Users**, not items | One shopper complaining ten times is still one user. |
| **At least one** | A doubt about one product is survivable — the shopper buys something else in the list. A doubt about *Myntra itself* blocks every saved item at once. |
| **Within 30 days** | "Waiting for the Diwali sale" is a real purchase that lands outside the window. Solving it does not move this metric. |

So the score is `share × severity × user-cost × in-window`, where the last two terms are measured per signal by `scripts/scope_tag.py` rather than assumed. That reordering is not cosmetic: **quality/authenticity doubts are 78% wishlist-wide against fit's 48%**, so quality costs more users per complaint even though fit appears more often.

The two scope terms are estimated on **YouTube comments only**. An app reviewer writes "always out of stock" where a shopper looking at one garment writes "sold out in M" — pooling them put `out_of_stock` at 87% wishlist-wide on app reviews against 30% on YouTube. Controlling for venue changes the *level* but not the *ordering*.

Buckets whose 95% confidence intervals overlap **share a rank**. At n≈1,500 the top three are not statistically separable, and the app says so instead of printing a 1, 2, 3 the data cannot support.

## 🎯 Key Strategic Insights at a Glance

* **15,661 Customer Signals Analyzed:** 7,449 Google Play reviews, 4,451 iOS App Store reviews (across 23 international storefronts), and 3,761 YouTube try-on haul comments — of which **1,505 carry a genuine wishlist signal**.
* **YouTube is 24% of the corpus but 69% of the signal.** App-store reviews are about the *app*; only 3.8–4.2% describe a purchase blocker. Try-on haul comments run at **27.6%**, because that is where people actually talk through fit and quality before buying.
* **Fit and quality lead, not price.** On app-store data alone the top blocker was "waiting for a discount". With try-on comments in, fit (25.3%) and quality/authenticity (24.3%) both overtake price (22.5%) — reordering the finding from one you can only solve with margin to two you can solve with product.
* **68% Addressable Without Discounting:** 1,023 of the 1,505 signals are solvable through UX and product interventions; a further 23% are waiting on a price drop, which no product change fixes.
* **Cross-Channel Behavior:** iOS users demonstrate higher sensitivity to product authenticity and styling curation compared to Android users.
* **Hybrid Intelligence Architecture:** Offline batch LLM schema extraction paired with an **In-Memory RAG Copilot** for instant qualitative and quantitative strategy synthesis.

---

## 🖥️ Live Dashboard Architecture (5 Tabs)

```
Wishlist Discovery Engine
├── Overview          The answer in one screen: headline finding, 4 KPI tiles,
│                     motives vs. blockers,
│                     platform divergence (collapsed by default)
├── Deep dives        3 strategic pillars behind one pill selector:
│                     intent, blockers & uncertainty, search leakage
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
Collect (15,661 items) ➔ Extract (LLM Router) ➔ Decouple Taxonomy ➔ Quantify & Rank ➔ Interactive Copilot
```

### Step 1: Multi-Channel Data Harvesting
```bash
python scripts/collect_playstore.py   # Scrapes 7,400+ long-form Google Play reviews
python scripts/collect_appstore.py    # Scrapes 4,400+ iOS reviews across 23 country storefronts
python scripts/collect_youtube.py     # Scrapes 3,700+ comments on Myntra try-on hauls & reviews
python scripts/prepare_new.py         # Dedups a fresh pull by id AND by normalised text
python scripts/classify_new.py --shard 0 --of 4   # Classifies only the new rows (shardable)
python scripts/scope_tag.py --shard 0 --of 4      # Tags each signal item- vs platform-scoped, and in/out of the 30-day window
python scripts/report_pdf.py          # Renders every signal by bucket to a PDF for review
python scripts/collect_manual.py      # Structured template for Reddit/forum qualitative inputs
```

### Step 2: AI Structured Batch Extraction
Processes raw text with an automatic **Gemini 3.5 Flash-Lite ➔ Groq `gpt-oss-120b` fallback router**. The lite model was chosen on measured accuracy, not cost: the reasoning models spent thousands of thinking tokens per batch and still missed short, blunt, emoji-heavy complaints.
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
│   ├── extracted.csv           # 15,661 structured customer signals (committed)
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
