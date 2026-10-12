#!/usr/bin/env python3
"""Restore research/institutions/<id>.json files from exports/database.json.

Used once on 12 Oct 2026, when the project was moved to a cloud session and only part of
research/institutions/ arrived. database.json (built 18:40) carries every field of each
institution file except where noted, so the files can be rebuilt in protocol form.

Known losses (logged once in research/central_edits.json, not in each file):
- disclosure_checks survive only for metrics with no recorded value (build_db folds them into kpi).
- Source `note` fields (e.g. "Seen in search results only") were not carried by build_db and are lost.

Usage:
  python3 tools/restore_from_db.py                # restore ids in database.json that have no file
  python3 tools/restore_from_db.py --check        # compare restorations with files that exist; write nothing
  python3 tools/restore_from_db.py --ids a,b      # restore specific ids (never overwrites unless --force)
"""
import argparse
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(ROOT, "exports", "database.json")
INST_DIR = os.path.join(ROOT, "research", "institutions")

TOP_KEYS = ["id", "name", "short_name", "legal_name", "name_ar", "country", "hq_city", "website",
            "linkedin_company", "category", "type", "model", "founded", "regulators", "listed", "exchange",
            "ticker", "parent_id", "ownership_summary", "shareholders", "government_link", "group_structure",
            "subsidiaries", "footprint", "customer_segments", "business_lines", "metrics", "disclosure_checks",
            "people", "capabilities", "sources", "original_reconciliation", "discrepancies", "open_items",
            "research_status", "researched_by", "checked"]
PERSON_DERIVED = {"person_id", "institution_id", "institution", "country", "linkedin_unverified_candidate",
                  "key_contact"}
METRIC_DERIVED = {"metric_id", "institution_id", "institution", "value_abs", "usd_bn", "fx_rate_per_usd",
                  "fx_basis", "standard_period", "auto_check"}
SOURCE_DERIVED = {"source_id", "institution_id", "local_id", "link_state", "link_code", "link_final_url",
                  "link_note"}
ROW_DERIVED = {"institution_id", "institution"}


def local_ids(obj, iid):
    """Strip the '<id>:' prefix that build_db adds to every source_ids entry."""
    pre = iid + ":"
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            if k == "source_ids" and isinstance(v, list):
                out[k] = [s[len(pre):] if isinstance(s, str) and s.startswith(pre) else s for s in v]
            else:
                out[k] = local_ids(v, iid)
        return out
    if isinstance(obj, list):
        return [local_ids(v, iid) for v in obj]
    return obj


def num(s):
    m = re.search(r"(\d+)$", s or "")
    return int(m.group(1)) if m else 0


def restore(db, iid):
    rec = next(i for i in db["institutions"] if i["id"] == iid)
    out = {}
    for k in TOP_KEYS:
        if k in rec:
            out[k] = local_ids(rec[k], iid)
    # metrics
    ms = sorted((m for m in db["metrics"] if m["institution_id"] == iid), key=lambda m: num(m["metric_id"]))
    out["metrics"] = [local_ids({k: v for k, v in m.items() if k not in METRIC_DERIVED}, iid) for m in ms]
    # disclosure checks (only those folded into kpi survive)
    dcs = []
    for metric, k in (rec.get("kpi") or {}).items():
        if isinstance(k, dict) and "disclosure" in k:
            dcs.append({"metric": metric, "status": k["disclosure"], "where_checked": k.get("where_checked")})
    out["disclosure_checks"] = dcs
    # people
    people = []
    for p in rec.get("people") or []:
        q = {k: v for k, v in p.items() if k not in PERSON_DERIVED}
        if p.get("linkedin_unverified_candidate") and not q.get("linkedin_url"):
            q["linkedin_url"] = p["linkedin_unverified_candidate"]
        people.append(local_ids(q, iid))
    out["people"] = people
    out["capabilities"] = local_ids(rec.get("capabilities") or {}, iid)
    srcs = sorted((s for s in db["sources"] if s["institution_id"] == iid), key=lambda s: num(s["local_id"]))
    out["sources"] = [dict({"id": s["local_id"]}, **{k: v for k, v in s.items() if k not in SOURCE_DERIVED})
                      for s in srcs]
    out["original_reconciliation"] = [local_ids({k: v for k, v in c.items() if k not in ROW_DERIVED}, iid)
                                      for c in db["corrections"] if c["institution_id"] == iid]
    out["discrepancies"] = [local_ids({k: v for k, v in d.items() if k not in ROW_DERIVED}, iid)
                            for d in db["discrepancies"] if d["institution_id"] == iid]
    out["open_items"] = [o["item"] for o in db["open_items"] if o["institution_id"] == iid]
    for k in ("research_status", "researched_by", "checked"):
        out[k] = rec.get(k)
    return {k: out.get(k) for k in TOP_KEYS}


def diff(a, b, path="", out=None, limit=40):
    out = [] if out is None else out
    if len(out) >= limit:
        return out
    if type(a) != type(b):
        out.append(f"{path}: type {type(a).__name__} vs {type(b).__name__}")
    elif isinstance(a, dict):
        for k in list(a) + [k for k in b if k not in a]:
            if k not in a:
                out.append(f"{path}.{k}: missing in restored")
            elif k not in b:
                out.append(f"{path}.{k}: extra in restored")
            else:
                diff(a[k], b[k], f"{path}.{k}", out, limit)
    elif isinstance(a, list):
        if len(a) != len(b):
            out.append(f"{path}: len {len(a)} vs {len(b)}")
        for i, (x, y) in enumerate(zip(a, b)):
            diff(x, y, f"{path}[{i}]", out, limit)
    elif a != b:
        out.append(f"{path}: {str(a)[:80]!r} vs {str(b)[:80]!r}")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--ids")
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    db = json.load(open(DB, encoding="utf-8"))
    ids = [i["id"] for i in db["institutions"]]
    if a.ids:
        ids = [i for i in a.ids.split(",") if i]
    if a.check:
        for iid in ids:
            p = os.path.join(INST_DIR, iid + ".json")
            if not os.path.exists(p):
                continue
            d = diff(restore(db, iid), json.load(open(p, encoding="utf-8")))
            print(f"{iid}: {'identical' if not d else str(len(d)) + ' differences'}")
            for line in d[:12]:
                print("   ", line)
        return
    done = 0
    for iid in ids:
        p = os.path.join(INST_DIR, iid + ".json")
        if os.path.exists(p) and not a.force:
            continue
        r = restore(db, iid)
        with open(p, "w", encoding="utf-8") as fh:
            json.dump(r, fh, ensure_ascii=False, indent=2)
            fh.write("\n")
        done += 1
    print(f"restored {done} files")


if __name__ == "__main__":
    sys.exit(main())
