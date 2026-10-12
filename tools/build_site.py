#!/usr/bin/env python3
"""Build the website from exports/database.json and tools/site_template.html.

Writes site/gcc-fi-intelligence.html (the artifact source) and site/preview.html (the same page wrapped in a full
HTML document for local viewing: `python3 -m http.server 8765 --bind 127.0.0.1` from site/).

The page embeds a trimmed copy of the database: institutions sorted by name with their metrics attached, people
without the table-only fields, sources keyed by source id. Rebuilt on 12 Oct 2026 in the cloud session; it
reproduces the 18:40 page byte for byte from the 18:40 database.
"""
import json
import os
import sys
from collections import OrderedDict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(ROOT, "exports", "database.json")
TEMPLATE = os.path.join(ROOT, "tools", "site_template.html")
SITE = os.path.join(ROOT, "site")
PLACEHOLDER = "__DATA_JSON__"

METRIC_KEYS = ["metric", "value", "unit", "currency", "value_abs", "usd_bn", "period_end", "period_label", "scope",
               "definition", "status", "locator", "note", "source_ids", "standard_period", "auto_check"]
PERSON_DROP = {"institution_id", "institution", "country", "linkedin_unverified_candidate", "key_contact"}
SOURCE_KEYS = ["institution_id", "local_id", "title", "publisher", "url", "doc_type", "tier", "published",
               "accessed", "link_state"]
PREVIEW_HEAD = ('<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" '
                'content="width=device-width,initial-scale=1,viewport-fit=cover"><style>[hidden]{display:none!important}'
                'body{margin:0}</style></head><body>')
PREVIEW_TAIL = "</body></html>"


def site_data(db):
    meta = OrderedDict(db["meta"])
    meta["universe"] = OrderedDict((k, v) for k, v in db["meta"]["universe"].items() if k != "version")
    by_inst = {}
    for m in db["metrics"]:
        by_inst.setdefault(m["institution_id"], []).append(OrderedDict((k, m[k]) for k in METRIC_KEYS))
    insts = []
    for i in sorted(db["institutions"], key=lambda i: i["name"]):
        r = OrderedDict(i)
        r["people"] = [OrderedDict((k, v) for k, v in p.items() if k not in PERSON_DROP) for p in i["people"]]
        r["metrics"] = by_inst.get(i["id"], [])
        insts.append(r)
    return OrderedDict([
        ("meta", meta), ("institutions", insts),
        ("sources", OrderedDict((s["source_id"], OrderedDict((k, s[k]) for k in SOURCE_KEYS)) for s in db["sources"])),
        ("corrections", db["corrections"]), ("discrepancies", db["discrepancies"]), ("open_items", db["open_items"])])


def main():
    db = json.load(open(DB, encoding="utf-8"), object_pairs_hook=OrderedDict)
    tpl = open(TEMPLATE, encoding="utf-8").read()
    if tpl.count(PLACEHOLDER) != 1:
        sys.exit(f"{TEMPLATE}: expected exactly one {PLACEHOLDER}")
    blob = json.dumps(site_data(db), ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    page = tpl.replace(PLACEHOLDER, blob)
    os.makedirs(SITE, exist_ok=True)
    with open(os.path.join(SITE, "gcc-fi-intelligence.html"), "w", encoding="utf-8") as fh:
        fh.write(page)
    with open(os.path.join(SITE, "preview.html"), "w", encoding="utf-8") as fh:
        fh.write(PREVIEW_HEAD + page + PREVIEW_TAIL)
    print(f"site/gcc-fi-intelligence.html: {len(page.encode('utf-8')) / 1e6:.2f} MB, "
          f"{len(db['institutions'])} institutions")


if __name__ == "__main__":
    sys.exit(main())
