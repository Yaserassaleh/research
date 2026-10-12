#!/usr/bin/env python3
"""Check every source URL in research/institutions/*.json and write exports/link_check.json.

States: ok (2xx) · blocked (401/403/429/999, bot protection; not evidence the page is gone) · broken (404/410)
· error (other HTTP status) · unreachable (DNS, TLS or timeout). URLs already checked are kept unless --all.

Usage: python3 tools/check_links.py [--all] [--workers 16]

Rebuilt on 12 Oct 2026 in the cloud session (the original script was not transferred); same output format.
"""
import argparse
import concurrent.futures as cf
import datetime as dt
import json
import os
import sys
import urllib.error
import urllib.request
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pdftext import UA, quote_url  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INST_DIR = os.path.join(ROOT, "research", "institutions")
OUT = os.path.join(ROOT, "exports", "link_check.json")
BLOCKED = {401, 403, 429, 999}
BROKEN = {404, 410}


def check(url):
    today = dt.date.today().isoformat()
    req = urllib.request.Request(quote_url(url), headers={"User-Agent": UA, "Accept": "*/*", "Range": "bytes=0-2047"})
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            code = r.status
            return {"code": code, "final_url": r.geturl(), "state": "ok" if code < 300 else "error", "checked": today}
    except urllib.error.HTTPError as e:
        state = "blocked" if e.code in BLOCKED else "broken" if e.code in BROKEN else "error"
        return {"code": e.code, "state": state, "checked": today}
    except Exception as e:
        return {"code": None, "state": "unreachable", "error": str(e)[:200], "checked": today}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true", help="re-check URLs that already have a result")
    ap.add_argument("--workers", type=int, default=16)
    a = ap.parse_args()
    urls = set()
    for f in sorted(os.listdir(INST_DIR)):
        if f.endswith(".json"):
            for s in json.load(open(os.path.join(INST_DIR, f), encoding="utf-8")).get("sources") or []:
                if (s.get("url") or "").startswith("http"):
                    urls.add(s["url"])
    old = {}
    if os.path.exists(OUT):
        old = json.load(open(OUT, encoding="utf-8")).get("results", {})
    todo = sorted(u for u in urls if a.all or u not in old)
    print(f"{len(urls)} unique URLs; checking {len(todo)}")
    results = {u: r for u, r in old.items() if u in urls and not a.all}
    with cf.ThreadPoolExecutor(max_workers=a.workers) as ex:
        for u, r in zip(todo, ex.map(check, todo)):
            results[u] = r
    summary = Counter(r["state"] for r in results.values())
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump({"summary": dict(summary.most_common()), "results": results}, fh, ensure_ascii=False, indent=1)
    print("  " + ", ".join(f"{k} {v}" for k, v in summary.most_common()))
    if summary.get("unreachable", 0) == len(results) and results:
        print("  every URL unreachable: is outbound web access allowed in this environment?")


if __name__ == "__main__":
    main()
