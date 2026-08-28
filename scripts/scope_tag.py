"""
scope_tag.py
------------
The business metric is "percentage of USERS who purchase at least one wishlist
item within 30 days". Two properties of a blocker decide how much it moves that
metric, and neither is in the extraction schema:

  blocker_scope    item     - blocks the one product being looked at. The user
                              can still convert on something else in the list,
                              so the metric survives.
                   platform - a doubt about Myntra itself (authenticity, seller
                              trust, sizing being unreliable across the board).
                              It taints every item at once, so the user buys
                              nothing and the metric is lost.
  resolves_in_30d  whether the blocker is one the shopper expects to clear
                   inside the measurement window at all. "Waiting for the next
                   sale" or "saving for Diwali" can be a genuine purchase that
                   simply lands on day 60 - out of window, not lost.

Shardable:  python scripts/scope_tag.py --shard 0 --of 4
Merge:      python scripts/scope_tag.py --merge
"""
import argparse, csv, glob, json, os, sys, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dotenv import load_dotenv
load_dotenv()

from extract import BATCH_SIZE
from llm import LLMRouter, ProviderError, parse_json_response

CORPUS = "data/extracted.csv"
OUT_DIR = "data/scope_tags"
FIELDS = ["id", "blocker_scope", "resolves_in_30d", "scope_confidence"]

SYSTEM = """You are analysing complaints from shoppers about a fashion e-commerce app (Myntra).

For each numbered item, decide TWO things about what is stopping this shopper buying.

1. blocker_scope
   "platform" - the doubt is about Myntra, its sellers or its data in general.
                It would apply to ANY item the shopper has saved, not just one.
                Examples: "Myntra sells first copies", "their size charts are
                always wrong", "I don't trust the quality here any more".
   "item"     - the doubt is about ONE specific product. The shopper could still
                happily buy a different item.
                Examples: "not sure if this dress will fit me", "this one is out
                of stock in M", "waiting for this jacket to go on sale".

2. resolves_in_30d
   "yes"     - the shopper could plausibly complete this purchase within 30 days
               if the doubt were answered (most fit, quality and stock doubts).
   "no"      - the shopper is deliberately waiting for something further out: a
               big seasonal sale, a festival, a wedding, a salary date, a trip.
   "unclear" - not enough information.

Also give scope_confidence: "high", "medium" or "low".

Return ONLY a JSON array, one object per numbered item:
[{"n":1,"blocker_scope":"platform","resolves_in_30d":"yes","scope_confidence":"high"}]

Judge only what the text actually says. Do not infer beyond it."""


def merge():
    rows, seen = {}, set()
    for f in sorted(glob.glob(os.path.join(OUT_DIR, "shard_*.csv"))):
        with open(f, newline="", encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                if r["id"] not in seen:
                    seen.add(r["id"]); rows[r["id"]] = r

    with open(CORPUS, newline="", encoding="utf-8") as fh:
        corpus = list(csv.DictReader(fh)); header = list(corpus[0].keys())
    for c in FIELDS[1:]:
        if c not in header:
            header.append(c)

    hit = 0
    for r in corpus:
        tag = rows.get(r["id"])
        for c in FIELDS[1:]:
            r[c] = tag.get(c, "") if tag else r.get(c, "")
        hit += bool(tag)
    with open(CORPUS, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=header, extrasaction="ignore")
        w.writeheader()
        for r in corpus:
            w.writerow(r)
    print(f"tagged {hit:,} of {len(corpus):,} rows -> {CORPUS}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--shard", type=int, default=0)
    ap.add_argument("--of", type=int, default=1)
    ap.add_argument("--merge", action="store_true")
    a = ap.parse_args()
    if a.merge:
        merge(); return

    os.makedirs(OUT_DIR, exist_ok=True)
    out_path = os.path.join(OUT_DIR, f"shard_{a.shard}.csv")
    with open(CORPUS, newline="", encoding="utf-8") as f:
        # Only rows that carry a blocker can have that blocker scoped.
        allr = [r for r in csv.DictReader(f)
                if str(r.get("relevant", "")).strip().lower() in ("true", "1")
                and (r.get("text") or "").strip()
                and str(r.get("current_blocker", "")).strip().lower() not in ("", "nan", "none")]
    mine = [r for i, r in enumerate(allr) if i % a.of == a.shard]

    done = set()
    if os.path.exists(out_path):
        with open(out_path, newline="", encoding="utf-8") as f:
            done = {r["id"] for r in csv.DictReader(f)}
    todo = [r for r in mine if r["id"] not in done]
    total = (len(todo) + BATCH_SIZE - 1) // BATCH_SIZE
    print(f"[shard {a.shard}/{a.of}] {len(todo)} rows, {total} batches", flush=True)
    if not todo:
        return

    router = LLMRouter(verbose=False)
    write_header = not os.path.exists(out_path)
    with open(out_path, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        if write_header:
            w.writeheader()
        for bi in range(total):
            batch = todo[bi * BATCH_SIZE:(bi + 1) * BATCH_SIZE]
            numbered = "\n\n".join(f"[{i+1}] {r['text'][:1200]}" for i, r in enumerate(batch))
            for attempt in range(4):
                try:
                    raw, _ = router.complete(SYSTEM, numbered, max_tokens=16000)
                    res = parse_json_response(raw)
                    if isinstance(res, dict):
                        res = res.get("results", [])
                    if len(res) < len(batch):
                        raise ValueError(f"truncated {len(res)}/{len(batch)}")
                    for i, row in enumerate(batch):
                        m = next((x for x in res if x.get("n") == i + 1), None)
                        if not m:
                            raise ValueError(f"missing n={i+1}")
                        w.writerow({"id": row["id"],
                                    **{c: m.get(c, "") for c in FIELDS[1:]}})
                    f.flush()
                    print(f"[{a.shard}] batch {bi+1}/{total}", flush=True)
                    break
                except (json.JSONDecodeError, ValueError) as e:
                    print(f"[{a.shard}] batch {bi+1} retry {attempt+1}: {str(e)[:50]}", flush=True)
                    time.sleep(3)
                except ProviderError as e:
                    print(f"[{a.shard}] providers failed: {str(e)[:60]}", flush=True); time.sleep(30)
            else:
                print(f"[{a.shard}] batch {bi+1} GAVE UP", flush=True)
    print(f"[shard {a.shard}] done", flush=True)


if __name__ == "__main__":
    main()
