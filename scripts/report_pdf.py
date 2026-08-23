"""
report_pdf.py
-------------
Renders every relevant signal in the corpus, grouped by blocker bucket, to a PDF
for manual cross-checking. One row per signal: source, severity, the shopper's
own words, and the fields the extractor assigned.

    python scripts/report_pdf.py [--corpus data/extracted_clean.csv]
"""
import argparse, html, os, sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from taxonomy import BUCKETS, bucket_label

# Same alias folding the app applies on load, so the PDF and the dashboard
# cannot disagree about which bucket a row belongs to.
CANONICAL = {
    "price": "price_waiting", "quality": "quality_authenticity_doubt",
    "fit": "fit_size_uncertainty", "availability": "out_of_stock",
    "styling": "styling_uncertainty", "delivery_returns": "other",
    "uncertainty": "other", "uncertainty_type": "other",
}
RESIDUAL = ("other", "none")
SOURCE_LABEL = {"playstore": "Google Play", "youtube": "YouTube"}
SEV_LABEL = {"3": "high", "2": "medium", "1": "low"}


def source_of(raw):
    raw = str(raw)
    if raw.startswith("appstore"):
        country = raw.split("_", 1)[1].upper() if "_" in raw else ""
        return f"App Store {country}".strip()
    return SOURCE_LABEL.get(raw, raw)


def esc(v):
    return html.escape(str(v)) if pd.notna(v) and str(v).strip() else ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", default="data/extracted_clean.csv")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()

    df = pd.read_csv(a.corpus)
    df = df[df["relevant"].astype(str).str.lower().isin(["true", "1"])].copy()
    key = df["current_blocker"].astype(str).str.strip().str.lower()
    df["bucket"] = key.replace(CANONICAL).where(key.ne("") & key.ne("nan"), "none")

    total = len(df)
    out = a.out or f"reports/corpus-{total}-by-bucket.pdf"
    os.makedirs("reports", exist_ok=True)

    # Named buckets by size, then the residuals last - the same ordering rule
    # the dashboard uses, so nothing unspecified can lead the document.
    counts = df["bucket"].value_counts()
    named = [b for b in counts.index if b not in RESIDUAL]
    order = named + [b for b in RESIDUAL if b in counts.index]

    src_counts = df["source"].apply(
        lambda s: "App Store" if str(s).startswith("appstore")
        else "Google Play" if s == "playstore" else "YouTube").value_counts()

    parts = [f"""<!doctype html><meta charset="utf-8"><title>Corpus by bucket</title><style>
@page {{ size: A4; margin: 14mm 12mm; }}
* {{ box-sizing: border-box; }}
body {{ font: 10pt/1.55 "DM Sans", -apple-system, Segoe UI, sans-serif; color: #1C1E2E; margin: 0; }}
h1 {{ font-size: 21pt; margin: 0 0 4px; letter-spacing: -.02em; }}
.sub {{ color: #5C6076; font-size: 9.5pt; margin-bottom: 16px; }}
.toc {{ border: 1px solid #E3E4EC; border-radius: 8px; padding: 12px 16px; margin-bottom: 20px; }}
.toc table {{ width: 100%; border-collapse: collapse; }}
.toc td {{ padding: 3px 0; font-size: 9.5pt; }}
.toc td.n {{ text-align: right; color: #5C6076; width: 70px; font-variant-numeric: tabular-nums; }}
h2 {{ font-size: 13pt; margin: 0 0 10px; padding: 8px 12px; background: #FFF0F4;
      border-left: 3px solid #FF3F6C; border-radius: 4px; break-after: avoid; }}
h2 span {{ float: right; font-weight: 400; color: #5C6076; font-size: 10pt; }}
section {{ break-before: page; }}
.row {{ border: 1px solid #E9EAF0; border-radius: 6px; padding: 8px 11px;
        margin-bottom: 7px; break-inside: avoid; }}
.meta {{ font-size: 8pt; color: #5C6076; margin-bottom: 4px; }}
.meta b {{ color: #1C1E2E; font-weight: 600; }}
.sev-high {{ color: #C2255C; font-weight: 600; }}
.txt {{ font-size: 9.5pt; }}
.tags {{ font-size: 8pt; color: #5C6076; margin-top: 4px; }}
.tags code {{ background: #F3F4F8; border-radius: 3px; padding: 1px 5px; font-size: 7.5pt; }}
</style>
<h1>Wishlist corpus — every relevant signal by bucket</h1>
<div class="sub">{total:,} relevant signals ·
{" · ".join(f"{v:,} {k}" for k, v in src_counts.items())} ·
grouped by assigned blocker, largest bucket first, residuals last</div>
<div class="toc"><table>"""]

    for b in order:
        n = counts[b]
        parts.append(f'<tr><td>{esc(bucket_label(b))}</td>'
                     f'<td class="n">{n:,} · {n/total*100:.1f}%</td></tr>')
    parts.append("</table></div>")

    for b in order:
        sub = df[df["bucket"] == b]
        parts.append(f'<section><h2>{esc(bucket_label(b))}'
                     f'<span>{len(sub):,} · {len(sub)/total*100:.1f}%</span></h2>')
        # Highest severity first so the strongest evidence is what you read first.
        sub = sub.assign(_s=pd.to_numeric(sub["severity"], errors="coerce").fillna(0))
        for _, r in sub.sort_values("_s", ascending=False).iterrows():
            sev = SEV_LABEL.get(str(r["severity"]).split(".")[0], "")
            cls = " sev-high" if sev == "high" else ""
            tags = [f"{lbl} <code>{esc(r[c])}</code>" for lbl, c in (
                ("motive", "save_motive"), ("uncertainty", "uncertainty_type"),
                ("category", "segment_category"), ("channel", "external_channel"),
                ("workaround", "workaround")) if esc(r[c]) and esc(r[c]) != "none"]
            parts.append(
                f'<div class="row"><div class="meta"><b>{esc(source_of(r["source"]))}</b>'
                + (f' · <span class="{cls.strip()}">severity {sev}</span>' if sev else "")
                + f' · id {esc(r["id"])[:28]}</div>'
                f'<div class="txt">{esc(r["text"])[:600]}</div>'
                + (f'<div class="tags">{" · ".join(tags)}</div>' if tags else "")
                + "</div>")
        parts.append("</section>")

    tmp = os.path.abspath("reports/.corpus_report.html")
    with open(tmp, "w", encoding="utf-8") as f:
        f.write("".join(parts))

    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        br = p.chromium.launch()
        pg = br.new_page()
        pg.goto("file://" + tmp)
        pg.pdf(path=out, format="A4", print_background=True,
               margin={"top": "14mm", "bottom": "14mm", "left": "12mm", "right": "12mm"})
        br.close()
    os.remove(tmp)
    print(f"{total:,} signals across {len(order)} buckets -> {out}")


if __name__ == "__main__":
    main()
