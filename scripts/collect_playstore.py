"""
collect_playstore.py
--------------------
STEP 1 of the pipeline: pull raw Myntra reviews from the Google Play Store.

No API key needed. No login needed. Just run it.

    python scripts/collect_playstore.py

Output: data/raw_playstore.csv
"""

import csv
import os
import time

from google_play_scraper import Sort, reviews

# Myntra's Android package name. You can find any app's package name
# in its Play Store URL: play.google.com/store/apps/details?id=THIS_BIT
APP_ID = "com.myntra.android"

# How many reviews to pull. Start with 2000 to test, raise to 5000-8000
# once you know it works. More reviews = better numbers in your deck,
# but also more LLM cost in step 3.
# Target 15000 to get a massive pool of reviews.
TARGET_COUNT = 15000

# Pull in batches so we can show progress and survive interruptions.
BATCH_SIZE = 200

OUTPUT_PATH = os.path.join("data", "raw_playstore.csv")


def fetch_reviews():
    """Fetch reviews using NEWEST and MOST_RELEVANT to bypass caps."""
    collected = []
    seen_ids = set()

    for sort_method in [Sort.NEWEST, Sort.MOST_RELEVANT, Sort.RATING]:
        print(f"Fetching with sort method: {sort_method}")
        token = None
        while len(collected) < TARGET_COUNT:
            try:
                batch, token = reviews(
                    APP_ID,
                    lang="en",
                    country="in",
                    sort=sort_method,
                    count=BATCH_SIZE,
                    continuation_token=token,
                )
            except Exception as e:
                print(f"  ! Error on batch: {e}")
                print("  Stopping early and saving what we have.")
                break

            if not batch:
                print("  No more reviews available for this sort method.")
                break

            for b in batch:
                if b['reviewId'] not in seen_ids:
                    seen_ids.add(b['reviewId'])
                    collected.append(b)

            print(f"  Collected {len(collected)} / {TARGET_COUNT}")

            if token is None:
                break

            time.sleep(1)  # be polite, avoid getting blocked
            
        if len(collected) >= TARGET_COUNT:
            break

    return collected[:TARGET_COUNT]


def save(rows):
    os.makedirs("data", exist_ok=True)

    with open(OUTPUT_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["id", "source", "text", "rating", "date", "url"])

        written = 0
        for r in rows:
            text = (r.get("content") or "").strip()

            # Skip very short reviews - "good app", "nice" tell you nothing
            # and you would pay LLM cost to learn that.
            if len(text) < 25:
                continue

            writer.writerow([
                r.get("reviewId", ""),
                "playstore",
                text,
                r.get("score", ""),
                r.get("at").isoformat() if r.get("at") else "",
                f"https://play.google.com/store/apps/details?id={APP_ID}",
            ])
            written += 1

    print(f"\nSaved {written} usable reviews to {OUTPUT_PATH}")
    print(f"(Dropped {len(rows) - written} reviews under 25 characters.)")


if __name__ == "__main__":
    print(f"Fetching Myntra Play Store reviews (target: {TARGET_COUNT})...\n")
    save(fetch_reviews())
