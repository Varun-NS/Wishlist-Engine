"""
reclassify.py
-------------
Re-runs the classifier over the already-extracted corpus and writes a fresh
dataset, without touching data/extracted.csv.

Why not re-run extract.py against the raw files: data/raw_youtube.csv is
header-only - the raw YouTube pull is gone - so a raw re-extract would silently
rebuild the corpus without its 692 YouTube signals. extracted.csv still holds
every row's text.

Shardable so several workers can run at once:
    python scripts/reclassify.py --shard 0 --of 5

Each shard writes data/reclassified/shard_<i>.csv and is resumable: re-running a
shard skips ids already present in its own file. Merge with --merge.
"""
import argparse, csv, glob, json, os, sys, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dotenv import load_dotenv
load_dotenv()

from extract import FIELDNAMES, BATCH_SIZE, build_system_prompt
from llm import LLMRouter, ProviderError, parse_json_response

SOURCE_PATH = "data/extracted.csv"
OUT_DIR = "data/reclassified"
MERGED_PATH = "data/extracted_clean.csv"


def merge():
    seen, rows = set(), []
    for f in sorted(glob.glob(os.path.join(OUT_DIR, "shard_*.csv"))):
        with open(f, newline="", encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                if r["id"] not in seen:
                    seen.add(r["id"])
                    rows.append(r)
    with open(MERGED_PATH, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDNAMES)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in FIELDNAMES})
    print(f"merged {len(rows)} unique rows -> {MERGED_PATH}")
    return len(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--shard", type=int, default=0)
    ap.add_argument("--of", type=int, default=1)
    ap.add_argument("--merge", action="store_true")
    a = ap.parse_args()

    if a.merge:
        merge()
        return

    os.makedirs(OUT_DIR, exist_ok=True)
    out_path = os.path.join(OUT_DIR, f"shard_{a.shard}.csv")

    with open(SOURCE_PATH, newline="", encoding="utf-8") as f:
        all_rows = [r for r in csv.DictReader(f) if (r.get("text") or "").strip()]
    mine = [r for i, r in enumerate(all_rows) if i % a.of == a.shard]

    done = set()
    if os.path.exists(out_path):
        with open(out_path, newline="", encoding="utf-8") as f:
            done = {r["id"] for r in csv.DictReader(f)}

    todo = [r for r in mine if r["id"] not in done]
    total = (len(todo) + BATCH_SIZE - 1) // BATCH_SIZE
    print(f"[shard {a.shard}/{a.of}] {len(mine)} rows, {len(done)} done, {len(todo)} to do "
          f"({total} batches)", flush=True)
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
                    # A short batch means the response was truncated. Writing the
                    # partial result would silently drop rows, so treat it as an
                    # error and retry instead.
                    if len(res) < len(batch):
                        raise ValueError(f"truncated: {len(res)}/{len(batch)}")
                    for i, row in enumerate(batch):
                        m = next((x for x in res if x.get("n") == i + 1), None)
                        if not m:
                            raise ValueError(f"missing result n={i+1}")
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
                    print(f"[{a.shard}] batch {bi+1}/{total} +{len(batch)} via {provider}", flush=True)
                    break
                except (json.JSONDecodeError, ValueError) as e:
                    print(f"[{a.shard}] batch {bi+1} retry {attempt+1}: {str(e)[:60]}", flush=True)
                    time.sleep(3)
                except ProviderError as e:
                    print(f"[{a.shard}] batch {bi+1} providers failed: {str(e)[:70]}", flush=True)
                    time.sleep(30)
                except Exception as e:
                    print(f"[{a.shard}] batch {bi+1} error: {str(e)[:70]}", flush=True)
                    time.sleep(5)
            else:
                print(f"[{a.shard}] batch {bi+1} GAVE UP", flush=True)

    print(f"[shard {a.shard}] done -> {out_path}", flush=True)


if __name__ == "__main__":
    main()
