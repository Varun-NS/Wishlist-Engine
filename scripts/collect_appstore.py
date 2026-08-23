"""
collect_appstore.py
-------------------
STEP 1d: pull Apple App Store reviews via Apple's public RSS feed.

No key, no login, no approval. Just runs.

THE LIMIT YOU NEED TO KNOW:
Apple caps the feed at 10 pages x 50 reviews = 500 reviews per app
PER COUNTRY STOREFRONT. This is Apple's limit, not a tool limit -
nothing gets around it.

TWO WAYS WE WORK WITHIN IT:
  1. Pull from multiple storefronts (India plus diaspora markets).
     8 storefronts x 500 = up to 4,000 reviews.
  2. Pull each storefront twice - sorted by most recent AND most
     helpful. There is overlap, but the sets differ, so you net
     extra unique reviews. Duplicates are removed automatically.

WHY BOTHER WHEN PLAY STORE GIVES YOU MORE:
In India, iOS skews premium. Your Play Store corpus is mostly budget
and mid-tier shoppers. This gives you a premium-segment sample you
would otherwise not have. Small n, high signal - and if your blockers
differ between the two, that is a real segment split for your deck.

    python scripts/collect_appstore.py

Output: data/raw_appstore.csv
"""

import csv
import json
import os
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

# ---------------------------------------------------------------
# HOW TO FIND THE APP ID (do this before your first run):
#   1. Search the app on the App Store website
#   2. Look at the URL - it ends with /id{NUMBERS}
#      e.g. apps.apple.com/in/app/myntra/id907394059
#   3. Paste the number below and remove this comment
#
# Verify it yourself rather than trusting a hardcoded value - app IDs
# occasionally change when apps are relisted.
# ---------------------------------------------------------------
APP_ID = "907394059"   # <-- VERIFY THIS against the live App Store URL

# Storefronts to pull from. "in" is your primary market; the rest are
# diaspora markets where the app sees real usage.
# Drop any that return nothing - not every app is listed everywhere.
# Apple caps the RSS feed at 500 reviews per storefront, so the only way to
# raise the ceiling is more storefronts. These are markets with meaningful
# Indian diaspora or Myntra availability.
COUNTRIES = ["in", "us", "gb", "ae", "sg", "ca", "au", "sa",
             "my", "nz", "ie", "za", "qa", "kw", "bh", "om",
             "hk", "np", "lk", "bd", "th", "id", "ph", "de"]

# Apple allows both. Running both nets extra unique reviews.
SORT_ORDERS = ["mostrecent", "mosthelpful"]

MAX_PAGES = 10   # Apple's hard limit. Raising this does nothing.

OUTPUT_PATH = os.path.join("data", "raw_appstore.csv")


def fetch_page(country, sort_by, page):
    """Fetch one page of reviews. Returns list of entries, or []."""
    url = (
        f"https://itunes.apple.com/{country}/rss/customerreviews/"
        f"page={page}/id={APP_ID}/sortby={sort_by}/json"
    )

    req = Request(url, headers={"User-Agent": "Mozilla/5.0 (research script)"})

    try:
        with urlopen(req, timeout=30) as r:
            data = json.loads(r.read().decode("utf-8"))
    except HTTPError as e:
        if e.code == 404:
            return []          # app not listed in this storefront
        print(f"    HTTP {e.code} on {country}/{sort_by}/p{page}")
        return []
    except (URLError, json.JSONDecodeError) as e:
        print(f"    Error on {country}/{sort_by}/p{page}: {e}")
        return []

    feed = data.get("feed", {})
    entries = feed.get("entry", [])

    # Apple returns a dict instead of a list when there is only one entry
    if isinstance(entries, dict):
        entries = [entries]

    # The first entry on page 1 is app metadata, not a review.
    # Real reviews have an "im:rating" field.
    return [e for e in entries if "im:rating" in e]


def parse_entry(entry, country):
    """Turn Apple's nested JSON into a flat row."""
    def get(path, default=""):
        node = entry
        for key in path:
            node = node.get(key, {}) if isinstance(node, dict) else {}
        return node if isinstance(node, str) else node.get("label", default)

    title = entry.get("title", {}).get("label", "")
    content = entry.get("content", {}).get("label", "")
    rating = entry.get("im:rating", {}).get("label", "")
    review_id = entry.get("id", {}).get("label", "")

    # Title often carries the sentiment summary; keep both.
    text = f"{title}. {content}".strip() if title else content

    return {
        "id": f"as_{country}_{review_id}",
        "source": f"appstore_{country}",
        "text": text[:4000],
        "rating": rating,
        "date": "",
        "url": f"https://apps.apple.com/{country}/app/id{APP_ID}",
    }


def main():
    if APP_ID == "REPLACE_ME":
        raise SystemExit("Set APP_ID at the top of this file first.")

    all_rows = {}          # keyed by id, so duplicates collapse automatically
    per_country = {}

    for country in COUNTRIES:
        before = len(all_rows)

        for sort_by in SORT_ORDERS:
            for page in range(1, MAX_PAGES + 1):
                entries = fetch_page(country, sort_by, page)

                if not entries:
                    break      # no more pages in this storefront/sort

                for e in entries:
                    row = parse_entry(e, country)

                    # Skip very short reviews - they cost money to
                    # classify and teach you nothing.
                    if len(row["text"]) < 25:
                        continue

                    all_rows[row["id"]] = row

                time.sleep(0.4)   # be polite

        added = len(all_rows) - before
        per_country[country] = added
        print(f"  {country}: +{added} unique reviews")

    os.makedirs("data", exist_ok=True)
    with open(OUTPUT_PATH, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(
            f, fieldnames=["id", "source", "text", "rating", "date", "url"]
        )
        w.writeheader()
        w.writerows(all_rows.values())

    print(f"\nSaved {len(all_rows)} unique reviews to {OUTPUT_PATH}")

    empty = [c for c, n in per_country.items() if n == 0]
    if empty:
        print(f"\nNo reviews from: {', '.join(empty)}")
        print("Either the app is not listed there, or the ID is wrong.")
        print("If ALL storefronts are empty, check APP_ID against the")
        print("live App Store URL.")

    print(
        "\nNote: Apple caps this feed at 500 reviews per storefront. "
        "Your iOS sample is small by design - treat it as a premium-segment "
        "signal, not a volume source."
    )


if __name__ == "__main__":
    print(f"Fetching App Store reviews for app {APP_ID}...\n")
    main()
