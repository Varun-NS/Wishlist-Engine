"""
prepare_new.py
--------------
Works out which freshly-scraped rows are genuinely new, and reports duplication.

Two kinds of duplicate matter:
  1. same id   - the same review re-collected (Play Store reviewId, App Store
                 as_<country>_<id>, YouTube comment id are all stable)
  2. same text - the SAME review surfaced under different ids. Apple issues a
                 different review id per storefront, so a diaspora reviewer can
                 appear in several countries; YouTube comments get reposted.

Output: data/raw_new.csv  (deduped, not yet classified)
"""
import csv, glob, os, re, sys, unicodedata

CORPUS = "data/extracted_clean.csv"
# Apple's RSS feed is a rolling window - a fresh pull loses older reviews as
# newer ones arrive - so the archived pulls are read too and the union kept.
RAW = ["data/raw_playstore.csv", "data/raw_appstore.csv", "data/raw_youtube.csv",
       "data/archive/raw_playstore.csv", "data/archive/raw_appstore.csv"]
OUT = "data/raw_new.csv"
MIN_LEN = 25


def norm(t):
    """Normalise for near-duplicate matching: case, whitespace, punctuation, emoji."""
    t = unicodedata.normalize("NFKC", str(t)).lower()
    t = re.sub(r"[^\w\s]", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def main():
    corpus_ids, corpus_texts = set(), set()
    if os.path.exists(CORPUS):
        with open(CORPUS, newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                corpus_ids.add(r["id"])
                corpus_texts.add(norm(r.get("text", ""))[:300])
    print(f"existing corpus: {len(corpus_ids):,} rows")

    seen_ids, seen_texts, new = set(), set(), []
    stats = {}
    for path in RAW:
        if not os.path.exists(path):
            print(f"  {path}: missing, skipped"); continue
        tot = dup_id = dup_text = short = fresh = 0
        with open(path, newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                tot += 1
                text = (r.get("text") or "").strip()
                key = norm(text)[:300]
                if len(text) < MIN_LEN:
                    short += 1; continue
                if r["id"] in corpus_ids or r["id"] in seen_ids:
                    dup_id += 1; continue
                if key in corpus_texts or key in seen_texts:
                    dup_text += 1; continue
                seen_ids.add(r["id"]); seen_texts.add(key)
                new.append(r); fresh += 1
        stats[path.replace("data/", "")] = (tot, dup_id, dup_text, short, fresh)

    print(f"\n{'file':30s} {'rows':>7s} {'dup id':>8s} {'dup text':>9s} {'too short':>10s} {'NEW':>7s}")
    print("-" * 76)
    for k, (t, di, dt, sh, fr) in stats.items():
        print(f"{k:30s} {t:7,} {di:8,} {dt:9,} {sh:10,} {fr:7,}")
    print("-" * 76)
    print(f"{'TOTAL':30s} {sum(v[0] for v in stats.values()):7,} "
          f"{sum(v[1] for v in stats.values()):8,} {sum(v[2] for v in stats.values()):9,} "
          f"{sum(v[3] for v in stats.values()):10,} {len(new):7,}")

    os.makedirs("data", exist_ok=True)
    with open(OUT, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["id", "source", "text", "rating", "date", "url"])
        w.writeheader()
        for r in new:
            w.writerow({k: r.get(k, "") for k in w.fieldnames})
    print(f"\nwrote {len(new):,} new rows -> {OUT}")


if __name__ == "__main__":
    main()
