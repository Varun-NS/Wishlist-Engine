# Wishlist Discovery Engine

An AI system that analyses public conversations about online fashion shopping to identify what prevents wishlisted items from being purchased.

---

## What this does

Raw text (Play Store + App Store reviews, YouTube comments, hand-gathered forum posts) goes in. Structured, countable data comes out, ranked into an opportunity table.

```
Collect  →  Extract  →  Validate  →  Quantify  →  Score
 (free)     (LLM)      (you)       (pandas)     (pandas)
```

The output is not a summary. It is a table saying *"occasion-pending blocks 12.7% of purchases at average severity 2.2, is unaddressed by the product today, and is in scope given the no-monetary-incentive constraint."*

---

## Setup — do this once

### 1. Install Python
Check you have it: open Terminal (Mac) or Command Prompt (Windows) and run

```bash
python3 --version
```

Need 3.9 or higher. If it errors, install from python.org.

### 2. Get the project onto your machine

Put this folder somewhere sensible, then in Terminal:

```bash
cd path/to/wishlist-engine
```

Everything below runs from this folder.

### 3. Create a virtual environment

This keeps the project's packages separate from your system. Skipping it causes mysterious errors later.

```bash
python3 -m venv venv
source venv/bin/activate          # Mac/Linux
venv\Scripts\activate             # Windows
```

Your prompt should now start with `(venv)`. **You need to re-run the activate line every time you open a new Terminal.**

### 4. Install packages

```bash
pip install -r requirements.txt
```

### 5. Add your keys

```bash
cp .env.example .env
```

Open `.env` in a text editor and paste in your real keys.

- **Gemini key (primary, free)**: aistudio.google.com → Get API key → Create API key in new project. No credit card needed in supported regions.
- **Groq key (fallback, free)**: console.groq.com → API Keys. No credit card.
- **YouTube key**: console.cloud.google.com → create a project → APIs & Services → Library → enable **YouTube Data API v3** → Credentials → Create API key. Free, instant, 10,000 quota units/day.

**No Reddit key.** Reddit closed self-service API registration in 2026 — new OAuth tokens need manual approval with 2–4 week queues, and the old `.json` endpoint trick returns 403. `collect_manual.py` handles Reddit content instead.

`.env` is already in `.gitignore`, so it will not get pushed to GitHub. Do not remove that line.

---

## Running the pipeline

### Step 1 — Collect (10 minutes)

```bash
python scripts/collect_playstore.py
python scripts/collect_appstore.py
python scripts/collect_youtube.py
python scripts/collect_manual.py --init
```

**Before running the App Store one**, open `scripts/collect_appstore.py` and verify `APP_ID` against the live App Store URL (`apps.apple.com/in/app/.../id{NUMBERS}`). App IDs occasionally change when apps are relisted.

The first three run unattended. The fourth creates a template you fill in by hand.

**Play Store** gives you volume — thousands of reviews, but most are about delivery and refunds.
**App Store** gives you a premium segment. Apple caps its feed at 500 reviews per country storefront, so the script pulls from eight storefronts and both sort orders to net a few thousand. Small n, but in India iOS skews premium — if blockers differ between platforms, that is a defensible segment split.
**YouTube** gives you reasoning — comments on Myntra haul and try-on videos are dense with fit, quality, and "should I buy this" talk.
**Manual** gives you the highest-quality items — Reddit threads, Quora answers, Instagram comments you read and judged worth keeping. Aim for 150. Do this while you are reading your first 100 comments for the taxonomy; it is the same activity.

When your manual sheet is filled in:

```bash
python scripts/collect_manual.py --build
```

### Step 2 — Read 100 comments yourself (1 hour, do not skip)

Open `data/raw_playstore.csv` in Excel. Read a hundred rows with no framework in your head. Note what people actually say.

Then open `scripts/taxonomy.py` and edit the buckets: add what you missed, delete what nobody mentions.

**This edit is your v0 → v1 revision, and it is worth a line in your deck.** Screenshot the taxonomy before and after so you can show what changed.

### Step 3 — Extract (free, ~20 min for 3,000 items)

**Confirm your model names first.** Model identifiers change; this asks each provider what your keys can actually reach:

```bash
python scripts/llm.py --list-models
```

If `GEMINI_MODEL` or `GROQ_MODEL` at the top of `scripts/llm.py` is not in that output, correct it. Then:

```bash
python scripts/extract.py
```

Safe to interrupt — it resumes from where it stopped. To start fresh, delete `data/extracted.csv`.

**Why Gemini first.** Gemini's free tier is limited by *requests per minute*, which large batches solve — so the script sends 20 items per call and paces itself. Groq's free tier is limited by *tokens per day*, which nothing solves; at this batch size it exhausts after roughly 10–20 batches. Groq is a genuine failover for when Gemini returns 429, not a second workhorse. The script logs which provider served each row, and prints the split at the end.

Creates `data/extracted.csv`.

Safe to interrupt — it resumes from where it stopped. To start completely fresh, delete `data/extracted.csv` first.

### Step 4 — Validate (45 minutes of your time)

```bash
python scripts/validate.py --make-sample
```

Open `data/validation_sample.csv`. Hide the three `model_` columns. Fill in the `my_` columns yourself. Save. Then:

```bash
python scripts/validate.py --score
```

Put the resulting agreement percentage on your deck.

### Step 5 — Look at the results

```bash
streamlit run app.py
```

Opens at `http://localhost:8501`.

Before you trust the opportunity ranking, edit `COVERAGE_GAP` at the top of `app.py`. Those numbers are placeholders — replace them with your own judgement after auditing what Myntra already ships. A blocker Myntra already solves well should score near 0.3; one it ignores entirely should be near 0.9.

---

## Deploying (this is the link you submit)

1. Create a **public** GitHub repo and push this folder.

   Confirm `.env` did **not** get pushed. If it did, revoke your API key immediately and generate a new one.

   `data/extracted.csv` **should** be pushed — the dashboard needs it. Raw files are gitignored to keep the repo small.

2. Go to **share.streamlit.io**, sign in with GitHub, click **New app**, pick your repo, set main file to `app.py`.

3. Before deploying, open **Advanced settings → Secrets** and paste:

   ```toml
   GEMINI_API_KEY = "your-gemini-key"
   GROQ_API_KEY = "your-groq-key"
   ```

4. Deploy. You get a public URL in about two minutes.

5. **Test it in an incognito window.** If it does not load there, it will not load for your reviewer either.

---

## Quota control

Both providers are free tiers, so there is no bill to worry about — but a reviewer clicking the live-demo tab repeatedly can exhaust your daily request quota. Gemini's free tier allows roughly 1,500 requests/day, which is generous, but if you are demoing to a group, consider running your full extraction the day *before* submission so the quota is fresh.

---

## Project structure

```
wishlist-engine/
├── app.py                      the dashboard you deploy
├── requirements.txt
├── .env.example                template — copy to .env
├── .gitignore
├── data/
│   ├── raw_playstore.csv       created by step 1
│   ├── raw_appstore.csv        created by step 1
│   ├── raw_youtube.csv         created by step 1
│   ├── manual_input.csv        you fill this in by hand
│   ├── raw_manual.csv          built from manual_input.csv
│   ├── extracted.csv           created by step 3  ← push this
│   └── validation_sample.csv   created by step 4
└── scripts/
    ├── taxonomy.py             your buckets — edit this after step 2
    ├── llm.py                  provider routing: Gemini → Groq
    ├── collect_playstore.py
    ├── collect_appstore.py
    ├── collect_youtube.py
    ├── collect_manual.py
    ├── extract.py              the extraction prompt lives here
    └── validate.py
```

---

## Troubleshooting

**`ModuleNotFoundError`** — virtual environment is not active. Re-run the `activate` line.

**Play Store returns nothing** — verify the package name is still `com.myntra.android` by checking the app's Play Store URL.

**App Store returns nothing from every storefront** — the `APP_ID` is wrong. Check it against the live App Store URL. If only *some* storefronts are empty, the app simply is not listed there; that is normal.

**App Store stops at ~500 per country** — that is Apple's hard limit, not a bug. Nothing gets around it.

**Extraction returns bad JSON repeatedly** — lower `BATCH_SIZE` in `extract.py` from 20 to 10. Large batches can overflow the response token limit.

**`404 model not found`** — run `python scripts/llm.py --list-models` and update `GEMINI_MODEL` / `GROQ_MODEL` in `scripts/llm.py`.

**Everything falls through to Groq, then dies** — your Gemini key is not working. Run `python scripts/llm.py` on its own to test providers individually.

**Validation agreement under 70%** — two of your buckets are overlapping and ambiguous. Merge them in `taxonomy.py`, delete `data/extracted.csv`, and re-run extraction.


---

## A note on sources

Reddit's official API is no longer self-service. Since the Responsible Builder Policy update of June 2026, all new OAuth access requires explicit approval, with reported queues of two to four weeks. The free tier still exists for non-commercial use at 100 queries per minute — the barrier is getting in, not cost.

For a deadline-driven project the practical answer is to read Reddit in a browser like any other person and record what you find via `collect_manual.py`. This is legitimate research and worth stating plainly on your methodology slide: mixed-method collection, automated where APIs permit, manual where they do not. That sentence reads as rigour, not as a workaround.
