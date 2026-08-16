"""
collect_manual.py
-----------------
STEP 1c: turn hand-gathered text into pipeline-ready data.

WHY THIS EXISTS:
Reddit's API is closed to new developers in 2026, but Reddit threads
are still readable in a browser by any human. Reading threads and
copying the useful comments is research, not scraping - and it is
completely legitimate to cite in your deck.

You will gather fewer items this way (100-200 rather than 3000). That
is fine. Hand-picked Reddit comments have a far higher hit rate than
scraped app reviews, where most text is about delivery and refunds.
150 relevant comments beats 3000 mostly-irrelevant ones.

HOW TO USE:

  1. Run this once to create the template:
        python scripts/collect_manual.py --init

  2. Open data/manual_input.csv in Excel or Google Sheets.

  3. Go browse. Suggested searches on reddit.com (logged in, normal
     browser - no API needed):
        site:reddit.com myntra wishlist
        site:reddit.com myntra size confusing
        site:reddit.com "saved items" online shopping india
        r/IndianFashionAddicts  - browse recent threads
        r/TwoXIndia             - search "myntra"
        r/india                 - search "online shopping size"

     Also worth mining:
        - Quora answers on Myntra sizing / returns
        - Amazon India review sections for fashion items
        - Instagram comment threads on fashion brand posts

  4. For each useful comment, paste ONE ROW:
        text  = the comment itself
        source = reddit / quora / instagram / forum
        url   = link to the thread (for your deck's evidence trail)

  5. Save as CSV, then run:
        python scripts/collect_manual.py --build

     This produces data/raw_manual.csv which extract.py picks up
     automatically alongside your other sources.

TIME BUDGET: about 90 minutes for 150 good comments. Do this while
you are reading your first 100 comments for the taxonomy anyway -
it is the same activity, you are just saving what you read.
"""

import argparse
import csv
import os

TEMPLATE_PATH = "data/manual_input.csv"
OUTPUT_PATH = "data/raw_manual.csv"


EXAMPLE_ROWS = [
    {
        "text": (
            "I have like 40 things saved on Myntra that I'll probably never buy. "
            "Half of them I saved because I couldn't decide between two similar "
            "kurtas and then just never went back."
        ),
        "source": "reddit",
        "url": "https://reddit.com/r/example/comments/abc123",
    },
    {
        "text": (
            "Honestly the biggest issue is sizing. I'm M in one brand and L in "
            "another on the same app. So I keep things in wishlist and wait till "
            "someone I know orders from that brand."
        ),
        "source": "reddit",
        "url": "https://reddit.com/r/example/comments/def456",
    },
]


def init():
    os.makedirs("data", exist_ok=True)

    if os.path.exists(TEMPLATE_PATH):
        print(f"{TEMPLATE_PATH} already exists - not overwriting.")
        print("Delete it first if you want a fresh template.")
        return

    with open(TEMPLATE_PATH, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["text", "source", "url"])
        w.writeheader()
        w.writerows(EXAMPLE_ROWS)

    print(f"Created {TEMPLATE_PATH} with 2 example rows.\n")
    print("Open it, DELETE the two examples, and paste your own findings.")
    print("Then run: python scripts/collect_manual.py --build")


def build():
    if not os.path.exists(TEMPLATE_PATH):
        raise SystemExit("Run --init first.")

    with open(TEMPLATE_PATH, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    out = []
    skipped = 0

    for i, r in enumerate(rows):
        text = (r.get("text") or "").strip()

        if len(text) < 40:
            skipped += 1
            continue

        out.append({
            "id": f"manual_{i:04d}",
            "source": (r.get("source") or "manual").strip(),
            "text": text[:4000],
            "rating": "",
            "date": "",
            "url": (r.get("url") or "").strip(),
        })

    with open(OUTPUT_PATH, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(
            f, fieldnames=["id", "source", "text", "rating", "date", "url"]
        )
        w.writeheader()
        w.writerows(out)

    print(f"Built {OUTPUT_PATH} with {len(out)} items.")
    if skipped:
        print(f"({skipped} rows skipped for being under 40 characters.)")
    print("\nextract.py will pick this up automatically on the next run.")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--init", action="store_true", help="create the template")
    p.add_argument("--build", action="store_true", help="convert to pipeline format")
    a = p.parse_args()

    if a.init:
        init()
    elif a.build:
        build()
    else:
        p.print_help()
