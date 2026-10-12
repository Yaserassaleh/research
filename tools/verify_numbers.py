#!/usr/bin/env python3
"""Look for each recorded metric value in its cited sources; write exports/number_check.json.

For every metric with a numeric value, open its sources in order (PDF or HTML) and search the text for the value
as printed. States:
  found        the value appears in a source in a printed form (e.g. 833,184 / 833184 / (529) / 2.7)
  approximate  only a rounded form appears (e.g. 23.0 or 23 for 22,977,762 thousand reported as 'AED 23bn')
  derived      not printed, and the metric's note or definition says it was computed or derived
  unreadable   no source could be read (blocked, scanned PDF, fetch error)
  not_found    sources were read but the value was not seen; check by hand
The check is a screen: small counts written in words ("six branches") or values split across PDF columns can
show as not_found even when correct.

Usage: PDF_CACHE=/tmp/gccfi_pdf python3 -E tools/verify_numbers.py [--ids a,b] [--all]
Results for metrics already checked are kept unless --all or --ids names the institution.

Rebuilt on 12 Oct 2026 in the cloud session (the original script was not transferred); same output format.
"""
import argparse
import json
import os
import re
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pdftext import document_pages  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INST_DIR = os.path.join(ROOT, "research", "institutions")
OUT = os.path.join(ROOT, "exports", "number_check.json")
DERIVED = re.compile(r"\b(derived|computed|calculated|implied|sum of|we added)\b", re.I)


def norm(text):
    """Collapse whitespace and normalise digit separators so '833, 184' and '833 184' read as '833,184'."""
    t = text.replace(" ", " ").replace(" ", " ").replace("٬", ",").replace("٫", ".")
    t = t.translate(str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789"))
    t = re.sub(r"(?<=\d)[ ](?=\d{3}\b)", ",", t)
    return re.sub(r"\s+", " ", t)


def printed_forms(v):
    """Exact printed forms of a value."""
    neg = v < 0
    a = abs(v)
    forms = set()
    if float(a).is_integer():
        i = int(a)
        forms |= {f"{i:,}", str(i)}
    else:
        s = repr(float(a)).rstrip("0").rstrip(".")
        dec = len(s.split(".")[1]) if "." in s else 0
        forms |= {s, f"{a:,.{dec}f}"}
    if neg:
        forms = {f"({f})" for f in forms} | {f"-{f}" for f in forms} | {f"–{f}" for f in forms} | forms
    return forms


def rounded_forms(v, unit):
    """Rounded forms: the value at a larger unit to 0-2 decimals (thousand -> million/billion, etc.)."""
    mult = {"unit": 1, "thousand": 1e3, "million": 1e6, "billion": 1e9}.get(unit, 1)
    a = abs(v) * mult
    out = set()
    for scale in (1e3, 1e6, 1e9, 1e12):
        x = a / scale
        if 1 <= x < 100000:
            for d in (0, 1, 2):
                r = round(x, d)
                out.add(f"{r:,.{d}f}")
                out.add(f"{r:.{d}f}")
    return {f for f in out if f not in ("0", "0.0", "0.00")}


def contains_number(text, form):
    return re.search(r"(?<![\d.,])" + re.escape(form) + r"(?![\d]|[.,]\d)", text) is not None


def check_metric(m, sources, cache):
    v = m.get("value")
    if not isinstance(v, (int, float)) or isinstance(v, bool):
        return None
    urls = [sources[s]["url"] for s in m.get("source_ids") or [] if s in sources and sources[s].get("url")]
    read, texts = 0, []
    for u in urls:
        try:
            pages, _ = cache.setdefault(u, document_pages(u))
        except Exception:
            cache[u] = ([], "error")
            continue
        text = norm(" ".join(pages))
        if not text.strip():
            continue
        read += 1
        texts.append((u, text))
        for f in sorted(printed_forms(v), key=len, reverse=True):
            if contains_number(text, f):
                return {"state": "found", "url": u, "matched": f}
    if not read:
        return {"state": "unreadable", "checked_urls": len(urls)}
    for _, text in texts:
        if any(contains_number(text, f) for f in rounded_forms(v, m.get("unit"))):
            return {"state": "approximate", "checked_urls": len(urls)}
    if DERIVED.search((m.get("note") or "") + " " + (m.get("definition") or "")):
        return {"state": "derived", "checked_urls": len(urls)}
    return {"state": "not_found", "checked_urls": len(urls)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ids", help="comma-separated institution ids to (re)check")
    ap.add_argument("--all", action="store_true")
    a = ap.parse_args()
    only = set(a.ids.split(",")) if a.ids else None
    results = {}
    if os.path.exists(OUT) and not a.all:
        results = json.load(open(OUT, encoding="utf-8")).get("results", {})
    cache = {}
    for f in sorted(os.listdir(INST_DIR)):
        if not f.endswith(".json"):
            continue
        iid = f[:-5]
        if only and iid not in only:
            continue
        d = json.load(open(os.path.join(INST_DIR, f), encoding="utf-8"))
        sources = {s.get("id"): s for s in d.get("sources") or []}
        for n, m in enumerate(d.get("metrics") or [], 1):
            mid = f"{iid}:M{n}"
            if mid in results and not (a.all or only):
                continue
            r = check_metric(m, sources, cache)
            if r:
                results[mid] = r
        print(f"  {iid}: done")
    summary = Counter(r["state"] for r in results.values())
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump({"summary": dict(summary.most_common()), "results": results}, fh, ensure_ascii=False, indent=1)
    print(", ".join(f"{k} {v}" for k, v in summary.most_common()))


if __name__ == "__main__":
    main()
