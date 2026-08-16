"""
validate.py
-----------
STEP 3: prove your extraction is trustworthy.

This is the step almost nobody does, and it is the cheapest way to look
like a serious researcher instead of someone who trusted an LLM.

HOW TO USE (about 45 minutes of your time):

  1. Run:  python scripts/validate.py --make-sample
     This creates data/validation_sample.csv with 50 random rows.

  2. Open that file in Excel/Sheets. It has empty columns:
     my_relevant, my_save_motive, my_current_blocker
     Read each comment and fill them in YOURSELF. Do not look at the
     model's answer while doing this - that defeats the purpose.

  3. Save it back as CSV, then run:  python scripts/validate.py --score

  4. You get an agreement percentage. Put that number on your deck:
     "82% agreement with manual coding on a 50-item holdout sample."

If agreement is under ~70%, your taxonomy is probably ambiguous - two
buckets are overlapping. Fix taxonomy.py and re-run extraction.
"""

import argparse
import csv
import os
import random

SAMPLE_PATH = "data/validation_sample.csv"
EXTRACTED_PATH = "data/extracted.csv"
SAMPLE_SIZE = 50


def make_sample():
    if not os.path.exists(EXTRACTED_PATH):
        raise SystemExit("Run extract.py first.")

    with open(EXTRACTED_PATH, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    random.seed(42)  # fixed seed = reproducible sample
    picked = random.sample(rows, min(SAMPLE_SIZE, len(rows)))

    with open(SAMPLE_PATH, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow([
            "id", "text",
            "my_relevant", "my_save_motive", "my_current_blocker",
            "model_relevant", "model_save_motive", "model_current_blocker",
        ])
        for r in picked:
            w.writerow([
                r["id"], r["text"],
                "", "", "",                       # you fill these
                r["relevant"], r["save_motive"], r["current_blocker"],
            ])

    print(f"Created {SAMPLE_PATH} with {len(picked)} rows.")
    print("\nNOW: open it, hide the three model_ columns, and fill in")
    print("the my_ columns yourself. Then run: python scripts/validate.py --score")


def score():
    if not os.path.exists(SAMPLE_PATH):
        raise SystemExit("Run --make-sample first.")

    with open(SAMPLE_PATH, encoding="utf-8") as f:
        rows = [r for r in csv.DictReader(f) if r["my_relevant"].strip()]

    if not rows:
        raise SystemExit("No hand-coded rows found. Fill in the my_ columns.")

    def agree(field):
        m, n = 0, 0
        for r in rows:
            mine = r[f"my_{field}"].strip().lower()
            model = (r[f"model_{field}"] or "").strip().lower()
            if not mine:
                continue
            n += 1
            if mine == model:
                m += 1
        return (m / n * 100) if n else 0, n

    print(f"\nHand-coded rows: {len(rows)}\n")
    for field in ["relevant", "save_motive", "current_blocker"]:
        pct, n = agree(field)
        print(f"  {field:20s}  {pct:5.1f}%  (n={n})")

    print("\nPut the save_motive number on your discovery-engine slide.")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--make-sample", action="store_true")
    p.add_argument("--score", action="store_true")
    a = p.parse_args()

    if a.make_sample:
        make_sample()
    elif a.score:
        score()
    else:
        p.print_help()
