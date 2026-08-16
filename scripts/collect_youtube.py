"""
collect_youtube.py
------------------
STEP 1b (REPLACES collect_reddit.py): pull YouTube comments.

WHY THIS INSTEAD OF REDDIT:
Reddit closed self-service API registration in 2026 - new OAuth tokens
need manual approval with reported 2-4 week queues. Not viable on a
project deadline.

YouTube's Data API is still free, self-service, and instant.

WHY YOUTUBE IS ACTUALLY GOOD FOR THIS:
Comments on Myntra haul / try-on / review videos are dense with exactly
the reasoning you need - fit, quality, "does it look like the picture",
"should I size up". People discuss purchase hesitation openly there in
a way they do not in app-store reviews.

SETUP (5 minutes, free):
  1. console.cloud.google.com  ->  create a project (any name)
  2. APIs & Services -> Library -> search "YouTube Data API v3" -> Enable
  3. APIs & Services -> Credentials -> Create Credentials -> API key
  4. Copy it into .env as YOUTUBE_API_KEY

Free quota is 10,000 units/day. Each search costs 100 units, each
comment page costs 1. You will not come close to the limit.

    python scripts/collect_youtube.py

Output: data/raw_youtube.csv
"""

import csv
import os
import time
from urllib.parse import urlencode
from urllib.request import urlopen

from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("YOUTUBE_API_KEY")
BASE = "https://www.googleapis.com/youtube/v3"

# Search terms that surface videos whose comment sections are full of
# purchase-decision talk. Tune these once you see what comes back.
SEARCH_TERMS = [
    "myntra haul review",
    "myntra try on haul",
    "myntra kurta haul honest review",
    "myntra size guide fit",
    "myntra vs ajio which is better",
    "online shopping fail india size",
    "myntra quality review honest",
    "indian ethnic wear online shopping tips",
]

VIDEOS_PER_TERM = 30
COMMENTS_PER_VIDEO = 100   # max the API allows per page

OUTPUT_PATH = os.path.join("data", "raw_youtube.csv")


def api_get(endpoint, params):
    params["key"] = API_KEY
    url = f"{BASE}/{endpoint}?{urlencode(params)}"
    with urlopen(url, timeout=30) as r:
        import json
        return json.loads(r.read().decode())


def find_videos(term):
    """Search for videos matching a term. Returns list of video IDs."""
    try:
        data = api_get("search", {
            "part": "id,snippet",
            "q": term,
            "type": "video",
            "maxResults": VIDEOS_PER_TERM,
            "relevanceLanguage": "en",
            "regionCode": "IN",
        })
        return [
            (item["id"]["videoId"], item["snippet"]["title"])
            for item in data.get("items", [])
        ]
    except Exception as e:
        print(f"  ! search '{term}': {e}")
        return []


def get_comments(video_id, video_title):
    """Fetch top-level comments for one video."""
    rows = []
    try:
        data = api_get("commentThreads", {
            "part": "snippet",
            "videoId": video_id,
            "maxResults": COMMENTS_PER_VIDEO,
            "order": "relevance",
            "textFormat": "plainText",
        })
    except Exception as e:
        # Comments disabled on a video is common and harmless
        print(f"    (skipped {video_id}: {e})")
        return rows

    for item in data.get("items", []):
        snip = item["snippet"]["topLevelComment"]["snippet"]
        text = (snip.get("textDisplay") or "").strip()

        # Short comments are noise: "nice", "love it", emoji only
        if len(text) < 40:
            continue

        rows.append({
            "id": item["id"],
            "source": "youtube",
            "text": text[:4000],
            "rating": "",
            "date": snip.get("publishedAt", ""),
            "url": f"https://youtube.com/watch?v={video_id}",
        })

    return rows


def main():
    if not API_KEY:
        raise SystemExit(
            "Missing YOUTUBE_API_KEY.\n\n"
            "Get one free in 5 minutes:\n"
            "  1. console.cloud.google.com -> create a project\n"
            "  2. APIs & Services -> Library -> enable 'YouTube Data API v3'\n"
            "  3. APIs & Services -> Credentials -> Create API key\n"
            "  4. Add to .env as:  YOUTUBE_API_KEY=your-key\n"
        )

    all_rows = []
    seen = set()

    for term in SEARCH_TERMS:
        print(f"\nSearching: {term}")
        for vid, title in find_videos(term):
            if vid in seen:
                continue
            seen.add(vid)
            comments = get_comments(vid, title)
            all_rows.extend(comments)
            print(f"  {title[:55]:<55} +{len(comments)}")
            time.sleep(0.3)

    os.makedirs("data", exist_ok=True)
    with open(OUTPUT_PATH, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(
            f, fieldnames=["id", "source", "text", "rating", "date", "url"]
        )
        w.writeheader()
        w.writerows(all_rows)

    print(f"\nSaved {len(all_rows)} comments from {len(seen)} videos "
          f"to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
