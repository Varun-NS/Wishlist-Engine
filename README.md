# 🛍️ Wishlist Discovery Engine — E-Commerce Customer Intelligence

An enterprise-grade AI research engine that ingests, categorizes, and quantifies **10,180+ real-world customer signals** across Google Play, Apple App Store, and YouTube to uncover what prevents wishlisted fashion products from converting to purchases on Myntra.

---

## 🎯 Key Strategic Insights at a Glance

* **10,180 Customer Signals Analyzed:** 5,846 Google Play Store reviews, 3,643 iOS App Store reviews (across 8 international storefronts), and 692 YouTube try-on haul comments.
* **100% Addressable Opportunities:** Sizing uncertainty (13.9%) and Fabric/Quality doubts (23.2%) are fully addressable through UX/product interventions without requiring price discounting.
* **Cross-Channel Behavior:** iOS users demonstrate higher sensitivity to product authenticity and styling curation compared to Android users.
* **Hybrid Intelligence Architecture:** Offline batch LLM schema extraction paired with an **In-Memory RAG Copilot** for instant qualitative and quantitative strategy synthesis.

---

## 🖥️ Live Dashboard Architecture (6 Structured Tabs)

```
Wishlist Discovery Engine
├── 📊 Tab 1: Executive Overview (KPIs, Motive vs. Blocker Analytics, Ranked Opportunity Matrix, Platform Divergence)
├── 🎯 Tab 2: Strategic Deep Dives (4 Clean Sub-Tabs: Intent, Blockers & Postponement, External Leakage, Prioritized ROI Roadmap)
├── 🤖 Tab 3: Ask the Corpus (AI Copilot with In-Memory RAG, 1-Click Prompt Chips, Ground Truth Citations)
├── 💬 Tab 4: Voice of Customer (2-Column Evidence Grid, Full-Text Search, Channel & Severity Filters, Behavioral Hacks)
├── ⚡ Tab 5: Live AI Extractor (Real-Time LLM Prompt Playground with UUID persistence to data/extracted.csv)
└── 🔬 Tab 6: Methodology & Architecture (Data Harvesting, Prompt Disentanglement, Opportunity Scoring Algorithm)
```

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
