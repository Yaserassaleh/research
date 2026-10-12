#!/usr/bin/env python3
"""Plan and measure the executive deep-dive (research/PEOPLE_DEEP_DIVE.md).

  python3 tools/people_pass.py plan       # write research/people_pass/plan.json (batches X01…, ARTA-score order)
  python3 tools/people_pass.py baseline   # snapshot coverage to research/people_pass/baseline.json
  python3 tools/people_pass.py coverage   # print coverage now vs the baseline

One pass per institution group: each agent reads a group's documents once and covers decision-makers (key ARTA
contact functions and chairs) first at full depth, then board, Shariah and other members. Parent and subsidiary
profiles stay in the same batch because they share bios.
"""
import json
import os
import re
import sys
from collections import Counter, OrderedDict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INST_DIR = os.path.join(ROOT, "research", "institutions")
OUT_DIR = os.path.join(ROOT, "research", "people_pass")
KEY = {"CEO", "Group CEO", "Deputy CEO", "Retail", "Affluent", "Private banking", "Wealth",
       "Investments / asset management", "Brokerage", "Digital", "Technology", "Innovation / partnerships",
       "Strategy", "Subsidiary CEO", "Chair"}
TARGET, MAX_GROUPS = 32, 4


def load_all():
    out = OrderedDict()
    for f in sorted(os.listdir(INST_DIR)):
        if f.endswith(".json"):
            out[f[:-5]] = json.load(open(os.path.join(INST_DIR, f), encoding="utf-8"))
    return out


def is_decision_maker(p):
    return bool(set(p.get("functions") or []) & KEY)


def groups(insts):
    """Institution groups: a profiled parent with its profiled subsidiaries."""
    parent = {iid: d.get("parent_id") for iid, d in insts.items()}
    root = {}
    for iid in insts:
        r = iid
        while parent.get(r) in insts and parent.get(r) != r:
            r = parent[r]
        root[iid] = r
    g = OrderedDict()
    for iid in insts:
        g.setdefault(root[iid], []).append(iid)
    return list(g.values())


def plan():
    """One pass per institution group (documents are read once); batches in ARTA-score order."""
    insts = load_all()
    db_path = os.path.join(ROOT, "exports", "database.json")
    score = {}
    if os.path.exists(db_path):
        score = {i["id"]: i["score"]["total"] for i in json.load(open(db_path, encoding="utf-8"))["institutions"]}
    items = []
    for g in groups(insts):
        n = sum(len(insts[i]["people"]) for i in g)
        dm = sum(1 for i in g for p in insts[i]["people"] if is_decision_maker(p))
        items.append((g, n, dm, max(score.get(i, 0) for i in g)))
    items.sort(key=lambda t: -t[3])
    batches, cur = [], None
    for g, n, dm, sc in items:
        if cur is None or cur["people"] + n > TARGET or len(cur["groups"]) >= MAX_GROUPS:
            cur = {"ids": [], "groups": [], "people": 0, "decision_makers": 0}
            batches.append(cur)
        cur["ids"] += g
        cur["groups"].append(g)
        cur["people"] += n
        cur["decision_makers"] += dm
    out = [{"batch": f"X{n:02d}", "ids": b["ids"], "people": b["people"], "decision_makers": b["decision_makers"]}
           for n, b in enumerate(batches, 1)]
    os.makedirs(OUT_DIR, exist_ok=True)
    json.dump({"batches": out}, open(os.path.join(OUT_DIR, "plan.json"), "w"), indent=1)
    print(f"{len(out)} batches, {sum(b['people'] for b in out)} people "
          f"({sum(b['decision_makers'] for b in out)} decision-makers)")
    for b in out:
        print(f"  {b['batch']} ({b['people']} people, {b['decision_makers']} decision-makers): {', '.join(b['ids'])}")


def stats(insts):
    s = Counter()
    for iid, d in insts.items():
        for p in d["people"]:
            grp = "decision" if is_decision_maker(p) else "other"
            for g in (grp, "all"):
                s[(g, "people")] += 1
                s[(g, "education")] += bool(p.get("education"))
                s[(g, "career_with_years")] += bool(re.search(r"(19|20)\d\d", p.get("previous_roles") or ""))
                s[(g, "qualifications")] += bool(p.get("qualifications"))
                s[(g, "appointed")] += bool(p.get("appointed"))
                s[(g, "linkedin_verified")] += (p.get("linkedin_status") or "").startswith("Verified")
                s[(g, "verified_current")] += p.get("role_status") == "Verified current"
                s[(g, "departed")] += p.get("role_status") == "Departed"
                s[(g, "rechecked")] += (p.get("checked") or "") > "2026-10-12"
    return {f"{g}.{k}": v for (g, k), v in s.items()}


def coverage():
    now = stats(load_all())
    base_path = os.path.join(OUT_DIR, "baseline.json")
    base = json.load(open(base_path)) if os.path.exists(base_path) else {}
    for g in ("decision", "all", "other"):
        n = now.get(f"{g}.people", 0)
        print(f"{g}: {n} people (baseline {base.get(f'{g}.people', '-')})")
        for k in ("education", "career_with_years", "qualifications", "appointed", "linkedin_verified",
                  "verified_current", "departed", "rechecked"):
            v, b = now.get(f"{g}.{k}", 0), base.get(f"{g}.{k}")
            print(f"  {k:20} {v:5} ({v / n:5.0%})" + (f"   baseline {b}" if b is not None else ""))


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "coverage"
    if cmd == "plan":
        plan()
    elif cmd == "baseline":
        os.makedirs(OUT_DIR, exist_ok=True)
        json.dump(stats(load_all()), open(os.path.join(OUT_DIR, "baseline.json"), "w"), indent=1)
        coverage()
    else:
        coverage()


if __name__ == "__main__":
    main()
