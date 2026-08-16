"""
extract.py
----------
STEP 2: the actual "AI" in your AI discovery engine.

Turns unstructured text into STRUCTURED DATA you can count. This is the
difference between "summarising reviews" (what the brief tells you not
to do) and analysis.

    python scripts/extract.py

Output: data/extracted.csv

PROVIDERS: Gemini first, Groq as fallback. See llm.py for why that
order. Before your first full run:

    python scripts/llm.py --list-models

to confirm the model names are current on your keys.

KEY DESIGN CHOICES - be ready to defend these:

1. NO KEYWORD PRE-FILTERING. Everything goes to the model; it marks
   items not_relevant. Filtering on "wishlist" before counting would
   bias the counts before we counted anything.

2. CONFIDENCE IS A REAL FIELD. The model can say "low", and you report
   what share of the corpus is low-confidence. Numbers with error bars
   get trusted.

3. RESUMABLE. Results append to disk after every batch. A crash at row
   2400 does not cost you the first 2400.
"""

import csv
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from llm import LLMRouter, ProviderError, parse_json_response
from taxonomy import BUCKETS, EXTERNAL_CHANNELS, UNCERTAINTY_TYPES

# Bigger batches than you might expect. Gemini's free tier limits
# REQUESTS per minute, not tokens, so fewer-and-larger calls finishes
# the corpus far faster. 20 items x ~150 batches = 3000 items.
BATCH_SIZE = 20

INPUT_FILES = [
    "data/raw_playstore.csv",
    "data/raw_appstore.csv",
    "data/raw_youtube.csv",
    "data/raw_manual.csv",
]

OUTPUT_PATH = "data/extracted.csv"

FIELDNAMES = [
    "id", "source", "url", "text",
    "relevant", "save_motive", "current_blocker",
    "uncertainty_type", "external_channel", "workaround",
    "segment_gender", "segment_category", "segment_price_tier", "segment_occasion",
    "severity", "evidence_quote", "confidence", "provider",
]


def build_system_prompt() -> str:
    bucket_lines = "\n".join(f"  - {k}: {v}" for k, v in BUCKETS.items())

    return f"""You are a product research analyst studying why people save fashion items to a wishlist on Indian e-commerce apps (Myntra, AJIO) but do not buy them.

You will receive numbered pieces of text: app reviews, YouTube comments, and forum posts.

For EACH item, decide first whether it says anything at all about shopping consideration, hesitation, saving, comparing, or deciding. Many app reviews are about delivery, refunds, app crashes, or customer service. Those are NOT relevant - set relevant=false and leave other fields null.

For relevant items, extract:

save_motive - why the person saved/considered the item rather than buying immediately:
{bucket_lines}

current_blocker - what is stopping the purchase NOW. Same list of values.
IMPORTANT: save_motive and current_blocker are different questions and often differ. Someone may have saved an item to compare (in_app_comparison) but now be blocked because it sold out (out_of_stock).

uncertainty_type - one of: {", ".join(UNCERTAINTY_TYPES)}

external_channel - where they went for information OUTSIDE the app: {", ".join(EXTERNAL_CHANNELS)}

workaround - short description of what they actually did to cope (e.g. "ordered two sizes and returned one", "asked friend on WhatsApp", "checked Amazon price"). Null if none described.

segment_gender - men | women | unclear
segment_category - ethnic | western | footwear | accessories | beauty | unclear
segment_price_tier - budget | mid | premium | unclear
segment_occasion - wedding | festival | work | casual | travel | none | unclear

severity - how much friction this caused:
  high   = explicitly abandoned or did not buy because of it
  medium = significant delay, effort, or frustration described
  low    = mild or passing mention

evidence_quote - the single most telling verbatim sentence, max 25 words, copied exactly from the text.

confidence - high | medium | low. Use "low" when inferring heavily from thin text. Be honest; low-confidence tagging is expected and useful.

Return ONLY JSON: an object with a single key "results" whose value is an array with one object per input item, in the same order.

{{"results": [{{"n": 1, "relevant": true, "save_motive": "...", "current_blocker": "...", "uncertainty_type": "...", "external_channel": "...", "workaround": "..." or null, "segment_gender": "...", "segment_category": "...", "segment_price_tier": "...", "segment_occasion": "...", "severity": "...", "evidence_quote": "...", "confidence": "..."}}]}}

For relevant=false items, set every field except "n" and "relevant" to null."""


def load_inputs():
    rows, seen = [], set()
    for path in INPUT_FILES:
        if not os.path.exists(path):
            print(f"  (skipping {path} - not found)")
            continue
        with open(path, encoding="utf-8") as f:
            n = 0
            for r in csv.DictReader(f):
                if r.get("text", "").strip() and r["id"] not in seen:
                    seen.add(r["id"])
                    rows.append(r)
                    n += 1
        print(f"  Loaded {n} from {path}")
    return rows


def already_done(path):
    if not os.path.exists(path):
        return set()
    with open(path, encoding="utf-8") as f:
        return {r["id"] for r in csv.DictReader(f)}


def process_batch(router, system_prompt, batch):
    numbered = "\n\n".join(
        f"[{i + 1}] {r['text'][:1200]}" for i, r in enumerate(batch)
    )

    raw, provider = router.complete(system_prompt, numbered, max_tokens=8000)
    results = parse_json_response(raw)

    out = []
    for i, row in enumerate(batch):
        match = next((r for r in results if r.get("n") == i + 1), None)
        if not match:
            continue
        out.append({
            "id": row["id"],
            "source": row["source"],
            "url": row.get("url", ""),
            "text": row["text"][:500],
            "relevant": match.get("relevant"),
            "save_motive": match.get("save_motive"),
            "current_blocker": match.get("current_blocker"),
            "uncertainty_type": match.get("uncertainty_type"),
            "external_channel": match.get("external_channel"),
            "workaround": match.get("workaround"),
            "segment_gender": match.get("segment_gender"),
            "segment_category": match.get("segment_category"),
            "segment_price_tier": match.get("segment_price_tier"),
            "segment_occasion": match.get("segment_occasion"),
            "severity": match.get("severity"),
            "evidence_quote": match.get("evidence_quote"),
            "confidence": match.get("confidence"),
            "provider": provider,
        })
    return out


def main():
    print("Initialising providers...")
    router = LLMRouter()

    print("\nLoading raw data...")
    rows = load_inputs()
    if not rows:
        raise SystemExit("\nNo input data. Run the collect_ scripts first.")

    done = already_done(OUTPUT_PATH)
    todo = [r for r in rows if r["id"] not in done]

    print(f"\nTotal items:       {len(rows)}")
    print(f"Already processed: {len(done)}")
    print(f"To process now:    {len(todo)}")

    if not todo:
        print("\nNothing to do. Delete data/extracted.csv to start over.")
        return

    total_batches = (len(todo) + BATCH_SIZE - 1) // BATCH_SIZE
    est_min = total_batches * 7 / 60
    print(f"Batches:           {total_batches} (~{est_min:.0f} min at Gemini free-tier pace)\n")

    system_prompt = build_system_prompt()

    os.makedirs("data", exist_ok=True)
    write_header = not os.path.exists(OUTPUT_PATH)

    with open(OUTPUT_PATH, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        if write_header:
            writer.writeheader()

        for bi in range(total_batches):
            batch = todo[bi * BATCH_SIZE:(bi + 1) * BATCH_SIZE]
            try:
                recs = process_batch(router, system_prompt, batch)
                for rec in recs:
                    writer.writerow(rec)
                f.flush()
                print(f"  Batch {bi + 1}/{total_batches}  (+{len(recs)} rows)")

            except json.JSONDecodeError:
                print(f"  ! Batch {bi + 1}: unparseable JSON, skipped")
            except ProviderError as e:
                print(f"  ! Batch {bi + 1}: all providers failed - {e}")
                print("    Pausing 60s before continuing...")
                time.sleep(60)
            except Exception as e:
                print(f"  ! Batch {bi + 1}: {e}")

    print(f"\nDone. Results in {OUTPUT_PATH}")
    print(router.report())


if __name__ == "__main__":
    main()
