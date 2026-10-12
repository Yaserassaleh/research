#!/usr/bin/env python3
"""Research status: missing institutions by batch, partial profiles, files newer than the last build.

A batch is done when every id in research/universe.json -> batches has research/institutions/<id>.json.
Usage: python3 tools/status.py
"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UNIVERSE = os.path.join(ROOT, "research", "universe.json")
INST_DIR = os.path.join(ROOT, "research", "institutions")
DB = os.path.join(ROOT, "exports", "database.json")


def main():
    u = json.load(open(UNIVERSE, encoding="utf-8"))
    names = u["names"]
    files = {f[:-5] for f in os.listdir(INST_DIR) if f.endswith(".json")}
    built = set()
    if os.path.exists(DB):
        built = {i["id"] for i in json.load(open(DB, encoding="utf-8"))["institutions"]}
    planned = [i for ids in u["batches"].values() for i in ids]

    print(f"Planned {len(planned)} · files {len(files & set(planned))} · in last build {len(built)}")
    print("\nMissing by batch:")
    n_missing = 0
    for b, ids in u["batches"].items():
        miss = [i for i in ids if i not in files]
        if miss:
            n_missing += len(miss)
            print(f"  {b}: " + ", ".join(f"{i} ({names.get(i, '?')})" for i in miss))
    if not n_missing:
        print("  none")

    partial, invalid = [], []
    for i in sorted(files):
        try:
            d = json.load(open(os.path.join(INST_DIR, i + ".json"), encoding="utf-8"))
        except ValueError as e:
            invalid.append(f"{i}: {e}")
            continue
        if d.get("research_status") != "Complete":
            partial.append(f"{i} ({len(d.get('people') or [])} people, {len(d.get('metrics') or [])} metrics, "
                           f"{len(d.get('open_items') or [])} open items)")
    print(f"\nPartial profiles ({len(partial)}):")
    for p in partial:
        print("  " + p)
    if invalid:
        print(f"\nInvalid JSON ({len(invalid)}):")
        for p in invalid:
            print("  " + p)
    unbuilt = sorted(files - built)
    print(f"\nFiles not yet in exports/database.json ({len(unbuilt)}): " + (", ".join(unbuilt) or "none"))
    unplanned = sorted(files - set(planned))
    if unplanned:
        print(f"\nFiles not in the universe ({len(unplanned)}): " + ", ".join(unplanned))


if __name__ == "__main__":
    main()
