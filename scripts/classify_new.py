"""
classify_new.py
---------------
Classifies data/raw_new.csv with the same prompt and taxonomy as the corpus,
then appends to data/extracted_clean.csv.

Shardable:  python scripts/classify_new.py --shard 0 --of 4
Merge:      python scripts/classify_new.py --merge
"""
import argparse, csv, glob, json, os, sys, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dotenv import load_dotenv
load_dotenv()

from extract import FIELDNAMES, BATCH_SIZE, build_system_prompt
from llm import LLMRouter, ProviderError, parse_json_response

SOURCE = "data/raw_new.csv"
OUT_DIR = "data/new_classified"
CORPUS = "data/extracted_clean.csv"


def merge_into_corpus():
    rows, seen = [], set()
    for f in sorted(glob.glob(os.path.join(OUT_DIR, "shard_*.csv"))):
        with open(f, newline="", encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                if r["id"] not in seen:
                    seen.add(r["id"]); rows.append(r)
    existing = []
    if os.path.exists(CORPUS):
        with open(CORPUS, newline="", encoding="utf-8") as fh:
            existing = list(csv.DictReader(fh))
    have = {r["id"] for r in existing}
    added = [r for r in rows if r["id"] not in have]
    with open(CORPUS, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDNAMES)
        w.writeheader()
        for r in existing + added:
            w.writerow({k: r.get(k, "") for k in FIELDNAMES})
    print(f"corpus {len(existing):,} + {len(added):,} new = {len(existing)+len(added):,} -> {CORPUS}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--shard", type=int, default=0)
    ap.add_argument("--of", type=int, default=1)
    ap.add_argument("--merge", action="store_true")
    a = ap.parse_args()
    if a.merge:
        merge_into_corpus(); return

    os.makedirs(OUT_DIR, exist_ok=True)
    out_path = os.path.join(OUT_DIR, f"shard_{a.shard}.csv")
    with open(SOURCE, newline="", encoding="utf-8") as f:
        allr = [r for r in csv.DictReader(f) if (r.get("text") or "").strip()]
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
    sp = build_system_prompt()
    write_header = not os.path.exists(out_path)
    with open(out_path, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDNAMES)
        if write_header:
            w.writeheader()
        for bi in range(total):
            batch = todo[bi * BATCH_SIZE:(bi + 1) * BATCH_SIZE]
            numbered = "\n\n".join(f"[{i+1}] {r['text'][:1200]}" for i, r in enumerate(batch))
            for attempt in range(4):
                try:
                    raw, provider = router.complete(sp, numbered, max_tokens=16000)
                    res = parse_json_response(raw)
                    if isinstance(res, dict):
                        res = res.get("results", [])
                    if len(res) < len(batch):
                        raise ValueError(f"truncated {len(res)}/{len(batch)}")
                    for i, row in enumerate(batch):
                        m = next((x for x in res if x.get("n") == i + 1), None)
                        if not m:
                            raise ValueError(f"missing n={i+1}")
                        w.writerow({
                            "id": row["id"], "source": row["source"], "url": row.get("url", ""),
                            "text": row["text"][:500],
                            **{k: m.get(k) for k in (
                                "relevant", "save_motive", "current_blocker", "uncertainty_type",
                                "external_channel", "workaround", "segment_gender",
                                "segment_category", "segment_price_tier", "segment_occasion",
                                "severity", "evidence_quote", "confidence")},
                            "provider": provider,
                        })
                    f.flush()
                    print(f"[{a.shard}] batch {bi+1}/{total} +{len(batch)}", flush=True)
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
