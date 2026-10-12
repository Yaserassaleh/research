#!/usr/bin/env python3
"""Build the ARTA GCC FI database from research/institutions/*.json.

Writes exports/database.json, exports/<table>.csv, exports/gcc_fi.sqlite and exports/qa_report.json.
Reads research/universe.json, research/fx.json, research/qa_accepted.json, research/structural_corrections.json,
research/relationships.json, research/original_workbook_ids.json, and (when present) exports/link_check.json
and exports/number_check.json written by tools/check_links.py and tools/verify_numbers.py.

Rebuilt on 12 Oct 2026 in the cloud session from the 18:40 outputs (the original script was not transferred);
it reproduces those outputs for the 75 institutions then built. Scoring rules follow the methodology printed on the
website (tools/site_template.html, 'What each component measures').

Usage:
  python3 tools/build_db.py                      # full build into exports/
  python3 tools/build_db.py --out DIR --only IDS # build a subset elsewhere (IDS: comma list or @file)
"""
import argparse
import csv
import datetime as dt
import json
import os
import re
import sqlite3
import sys
from collections import OrderedDict
from decimal import ROUND_HALF_UP, Decimal

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESEARCH = os.path.join(ROOT, "research")
INST_DIR = os.path.join(RESEARCH, "institutions")
EXPORTS = os.path.join(ROOT, "exports")

AS_OF = "2026-10-12"
STD_BS = "2026-06-30"
STD_INCOME_END = "2025-12-31"
INCOME_METRICS = {"operating_income", "net_profit"}
BS_KPI = ("total_assets", "customer_deposits")
WEIGHTS = OrderedDict([("wealth", 25), ("scale", 15), ("gap", 20), ("momentum", 20), ("shelf", 10), ("access", 10)])
CAP_FIELDS = ["private_banking", "asset_management", "brokerage", "digital_investing", "advisory", "discretionary",
              "model_portfolios_robo", "funds_platform", "structured_products", "private_markets", "islamic_wealth"]
CAP_LABELS = OrderedDict([("private_banking", "Private banking"), ("asset_management", "Asset management"),
                          ("brokerage", "Brokerage"), ("digital_investing", "Digital investing"),
                          ("advisory", "Advisory"), ("discretionary", "Discretionary mandates"),
                          ("model_portfolios_robo", "Model portfolios / robo"), ("funds_platform", "Funds platform"),
                          ("structured_products", "Structured products"), ("private_markets", "Private markets"),
                          ("islamic_wealth", "Islamic wealth")])
COUNTRY_NAMES = {"AE": "United Arab Emirates", "SA": "Saudi Arabia", "QA": "Qatar", "KW": "Kuwait",
                 "BH": "Bahrain", "OM": "Oman"}
UNIT_MULT = {"unit": 1, "thousand": 1e3, "million": 1e6, "billion": 1e9}
MISSING = ("No", "Not found after research")
KEY_CONTACT_FUNCTIONS = {"CEO", "Group CEO", "Deputy CEO", "Retail", "Affluent", "Private banking", "Wealth",
                         "Investments / asset management", "Brokerage", "Digital", "Technology",
                         "Innovation / partnerships", "Strategy", "Subsidiary CEO"}
DECISION_FUNCTIONS = {"Affluent", "Brokerage", "Digital", "Innovation / partnerships",
                      "Investments / asset management", "Private banking", "Technology", "Wealth"}
AFFLUENT_TIERS = {"Affluent", "HNW", "Priority", "Private"}
# Access base points by recorded ARTA relationship (prefix of the relationship text).
RELATIONSHIP_BASE = [("Live ARTA partner", 5), ("Active opportunity", 4), ("Paused", 3), ("Profile delivered", 3),
                     ("Prior contact", 3), ("Research delivered", 3), ("Prior meeting", 3),
                     ("Added at user request", 2), ("Named in", 2), ("Declined", 2)]
AUM_SUBSTITUTION = re.compile(r"fiduciary assets|custody assets|customer deposits|investment securities", re.I)

VOCAB = {
    "category": {"Bank", "Bank-owned investment subsidiary", "Non-bank", "International bank (GCC operations)"},
    "type": {"Universal / commercial bank", "Islamic commercial bank", "Digital bank", "Private / investment bank",
             "Wholesale bank", "Asset & wealth manager", "Brokerage / investment platform",
             "Digital wealth platform", "Investment bank / alternatives manager", "Diversified finance company"},
    "model": {"Conventional", "Islamic", "Conventional with Islamic window/subsidiary", "Not applicable"},
    "country": set(COUNTRY_NAMES),
    "metric_status": {"Verified", "Conflicting sources", "Requires verification"},
    "disclosure_status": {"Not publicly disclosed", "Not found after research"},
    "role_status": {"Verified current", "Requires verification", "Conflicting sources", "Departed"},
    "linkedin_status": {"Verified (official link)", "Verified (profile/search match)", "Not verified", "Not checked"},
    "present": {"Yes", "No", "Not found after research", "Unclear"},
    "partner_status": {"Live", "Announced", "MoU / pilot", "Ended", "Unclear"},
    "functions": {"Chair", "Board", "Group CEO", "CEO", "Deputy CEO", "Retail", "Affluent", "Private banking",
                  "Wealth", "Investments / asset management", "Brokerage", "Digital", "Technology",
                  "Innovation / partnerships", "Strategy", "Subsidiary CEO", "Finance", "Treasury",
                  "Corporate / wholesale", "Operations", "Islamic / Shariah", "Other"},
    "period_type": {"point_in_time", "duration"},
    "research_status": {"Complete", "Partial"},
}


def load(path, default=None):
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def prefixed(obj, iid):
    """Deep copy with every source_ids entry prefixed '<iid>:'."""
    if isinstance(obj, dict):
        return OrderedDict((k, [f"{iid}:{s}" for s in v] if k == "source_ids" and isinstance(v, list)
                            else prefixed(v, iid)) for k, v in obj.items())
    if isinstance(obj, list):
        return [prefixed(v, iid) for v in obj]
    return obj


# ---------------------------------------------------------------- FX
def fx_for(m, fx):
    cur, unit = m.get("currency"), m.get("unit")
    if not cur or unit == "percent":
        return None, ""
    if cur in fx["pegged"]:
        return fx["pegged"][cur]["rate"], "peg"
    if cur == "KWD":
        k = fx["KWD"]
        end = m.get("period_end") or ""
        if m.get("period_type") == "duration":
            if end == "2025-12-31" and "FY2025" in k["average_rates"]:
                return k["average_rates"]["FY2025"]["rate"], "CBK FY2025 average"
            if end == "2026-06-30" and "H1 2026" in k["average_rates"]:
                return k["average_rates"]["H1 2026"]["rate"], "CBK H1 2026 average"
        if end in k["point_rates"]:
            return k["point_rates"][end], f"CBK rate at {end}"
        earlier = sorted(d for d in k["point_rates"] if d <= end)
        if earlier:
            d = earlier[-1]
            return k["point_rates"][d], f"CBK rate at {d} (nearest earlier; none for {end})"
        return None, f"no CBK rate for {end or 'undated'}"
    return None, f"unsupported currency {cur}"


def enrich_metric(iid, name, n, m, fx, numcheck):
    mid = f"{iid}:M{n}"
    v, unit = m.get("value"), m.get("unit")
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        value_abs = v * UNIT_MULT.get(unit, 1)
    else:
        value_abs = None
    rate, basis = fx_for(m, fx)
    usd = round(value_abs / rate / 1e9, 4) if (rate and value_abs is not None) else None
    end = m.get("period_end") or ""
    std = (end == STD_INCOME_END) if m.get("metric") in INCOME_METRICS else (end == STD_BS)
    nc = (numcheck or {}).get(mid)
    return OrderedDict([
        ("metric_id", mid), ("institution_id", iid), ("institution", name), ("metric", m.get("metric")),
        ("value", v), ("unit", unit), ("currency", m.get("currency")), ("value_abs", value_abs), ("usd_bn", usd),
        ("fx_rate_per_usd", rate), ("fx_basis", basis), ("period_end", m.get("period_end")),
        ("period_label", m.get("period_label")), ("period_type", m.get("period_type")), ("scope", m.get("scope")),
        ("definition", m.get("definition")), ("status", m.get("status")), ("locator", m.get("locator")),
        ("note", m.get("note")), ("source_ids", [f"{iid}:{s}" for s in m.get("source_ids") or []]),
        ("standard_period", std), ("auto_check", nc["state"] if nc else "not run")])


def pick_kpi(metrics, key, category=None):
    # International banks are compared at GCC scope: their global group figures stay in metrics but never
    # become headline figures (structural correction 'Standard Chartered figures').
    cands = [m for m in metrics if m["metric"] == key
             and not (m["scope"] or "").startswith("Segment:")
             and not ((m["scope"] or "").startswith("Subsidiary:") and key != "aum")
             and not (category == "International bank (GCC operations)"
                      and (m["scope"] or "").startswith("Group (global)"))]
    if not cands:
        return None
    std = [m for m in cands if m["standard_period"]]
    if std:
        return std[0]
    return sorted(cands, key=lambda m: m["period_end"] or "", reverse=True)[0]


def kpi_entry(m):
    return OrderedDict((k, m[k]) for k in ("value", "unit", "currency", "usd_bn", "value_abs", "period_end",
                                           "period_label", "standard_period", "scope", "status", "metric_id",
                                           "source_ids"))


# ---------------------------------------------------------------- scoring
def kusd(kpi, k):
    v = kpi.get(k) or {}
    return v.get("usd_bn")


def size_band(rec):
    kpi = rec["kpi"]
    if rec["category"] in ("Bank", "International bank (GCC operations)"):
        ta = kusd(kpi, "total_assets")
        if ta is None:
            return "Not disclosed"
        return ("Mega (≥ USD 150bn)" if ta >= 150 else "Large (USD 50–150bn)" if ta >= 50
                else "Mid (USD 15–50bn)" if ta >= 15 else "Small (< USD 15bn)")
    a = aum_measure(kpi)
    if a is None:
        return "Not disclosed"
    return ("≥ USD 20bn AUM" if a >= 20 else "USD 5–20bn AUM" if a >= 5 else "USD 1–5bn AUM" if a >= 1
            else "< USD 1bn AUM")


def aum_measure(kpi):
    for k in ("aum", "aua", "wealth_client_assets"):
        if kusd(kpi, k) is not None:
            return kusd(kpi, k)
    return None


def score(rec, rel, partners, initiatives):
    c, kpi = rec["capabilities"], rec["kpi"]
    comp = OrderedDict()
    # wealth franchise
    parts, s = [], 0
    if c["private_banking"]["present"] == "Yes":
        parts.append("private banking"); s += 1.5
    if {(g.get("tier") or "") for g in c.get("segments") or []} & AFFLUENT_TIERS:
        parts.append("affluent/priority tier"); s += 1
    if c["asset_management"]["present"] == "Yes":
        parts.append("asset management"); s += 1
    if c["brokerage"]["present"] == "Yes":
        parts.append("brokerage"); s += 0.75
    if c["advisory"]["present"] == "Yes" or c["discretionary"]["present"] == "Yes":
        parts.append("advisory/discretionary"); s += 0.75
    wealth = round(min(5, s), 2)
    comp["wealth"] = OrderedDict([("score", wealth), ("why", ", ".join(parts) or "no wealth lines evidenced")])
    # scale
    if rec["category"] in ("Bank", "International bank (GCC operations)"):
        ta = kusd(kpi, "total_assets")
        if ta is None:
            comp["scale"] = OrderedDict([("score", 1.0), ("why", "Total assets not available")])
        else:
            s = 5 if ta >= 150 else 4 if ta >= 75 else 3 if ta >= 30 else 2 if ta >= 10 else 1 if ta >= 3 else 0.5
            comp["scale"] = OrderedDict([("score", s), ("why", f"Total assets USD {ta:.1f}bn")])
    else:
        a = aum_measure(kpi)
        if a is None:
            ta = kusd(kpi, "total_assets")
            why = "AUM not disclosed" + (f"; balance sheet USD {ta:.1f}bn" if ta is not None else "")
            comp["scale"] = OrderedDict([("score", 1.0), ("why", why)])
        else:
            s = 5 if a >= 50 else 4 if a >= 20 else 3 if a >= 5 else 2 if a >= 1 else 1
            comp["scale"] = OrderedDict([("score", s), ("why", f"AUM/AUA/client assets USD {a:.1f}bn")])
    # digital-investing gap
    vendors = len((c.get("evidence_for_arta") or {}).get("incumbent_vendors") or [])
    di, mp = c["digital_investing"]["present"], c["model_portfolios_robo"]["present"]
    if di in MISSING:
        g, why = 5, "no in-app/online investing found"
    elif di == "Unclear" or mp == "Unclear":
        g, why = 3, "digital capability unclear"
    elif mp == "Yes":
        g, why = 2, "already offers digital model portfolios/robo"
    else:
        g, why = 4, "digital investing without model portfolios/robo"
    if vendors:
        g -= 1
        why += f"; incumbent vendor(s): {vendors}"
    comp["gap"] = OrderedDict([("score", g), ("why", why)])
    # momentum
    n = sum(1 for r in partners + initiatives if (r.get("date") or "")[:4] in ("2025", "2026"))
    m = 5 if n >= 8 else 4 if n >= 5 else 3 if n >= 3 else 2 if n >= 1 else 1
    comp["momentum"] = OrderedDict([("score", m), ("why", f"{n} dated initiatives/partnerships in 2025–2026")])
    # product-shelf fit
    pts, parts = 0, []
    if c["private_markets"]["present"] in MISSING:
        pts += 2; parts.append("no private markets")
    if c["model_portfolios_robo"]["present"] in MISSING:
        pts += 2; parts.append("no model portfolios")
    if c["structured_products"]["present"] in MISSING:
        pts += 1; parts.append("no structured products")
    sh = max(1, min(5, pts))
    if wealth <= 1 and di != "Yes" and sh > 2:
        sh = 2
        parts.append("little wealth activity to attach to")
    comp["shelf"] = OrderedDict([("score", sh), ("why", ", ".join(parts) or "shelf already broad")])
    # access & relationship
    nd = sum(1 for p in rec["people"] if p["role_status"] == "Verified current"
             and set(p["functions"] or []) & DECISION_FUNCTIONS)
    base = 1
    if rel:
        base = next((b for k, b in RELATIONSHIP_BASE if rel.startswith(k)), 2)
    comp["access"] = OrderedDict([("score", min(5, base + (1 if nd >= 2 else 0))),
                                  ("why", f"{rel or 'No recorded ARTA relationship'}; {nd} verified wealth/digital decision-makers")])
    # Half-up rounding, as Excel's ROUND() in the workbook and toFixed() on the website (72.25 -> 72.3).
    raw = sum(comp[k]["score"] * w / 5 for k, w in WEIGHTS.items())
    total = float(Decimal(repr(raw)).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP))
    tier = "Tier 1" if total >= 65 else "Tier 2" if total >= 50 else "Tier 3"
    flags = []
    if rel and rel.startswith("Live ARTA partner"):
        flags.append("Existing ARTA partner")
    if rec["model"] == "Islamic":
        flags.append("Islamic: needs Shariah-screened shelf")
    if rec["country"] == "SA":
        flags.append("KSA: CMA-licensed contracting entity; in-Kingdom data rules")
    if rec["category"] == "Non-bank" and mp == "Yes":
        flags.append("Runs own digital wealth product: may compete as well as partner")
    return OrderedDict([("components", comp), ("total", total), ("tier", tier), ("flags", flags)])


# ---------------------------------------------------------------- build
TOP_COPY = ["id", "name", "short_name", "legal_name", "name_ar", "country", "hq_city", "website", "linkedin_company",
            "category", "type", "model", "founded", "regulators", "listed", "exchange", "ticker", "parent_id",
            "ownership_summary", "shareholders", "government_link", "group_structure", "subsidiaries", "footprint",
            "customer_segments", "business_lines", "research_status", "researched_by", "checked"]
PERSON_KEYS = ["name", "name_ar", "title", "functions", "entity", "business_unit", "scope", "appointed",
               "appointed_note", "previous_roles", "education", "qualifications", "linkedin_url",
               "linkedin_unverified_candidate", "linkedin_status", "role_status", "role_evidence", "source_ids",
               "checked"]


def build(only=None):
    universe = load(os.path.join(RESEARCH, "universe.json"))
    fx = load(os.path.join(RESEARCH, "fx.json"))
    rels = load(os.path.join(RESEARCH, "relationships.json"), {})
    original_ids = set(load(os.path.join(RESEARCH, "original_workbook_ids.json"), []))
    links = (load(os.path.join(EXPORTS, "link_check.json"), {}) or {}).get("results", {})
    numcheck = (load(os.path.join(EXPORTS, "number_check.json"), {}) or {}).get("results", {})
    qa_extra = {"invalid_json": [], "broken_source_refs": [], "vocabulary_errors": []}

    files = sorted(f for f in os.listdir(INST_DIR) if f.endswith(".json"))
    raw = OrderedDict()
    for f in files:
        iid = f[:-5]
        if only is not None and iid not in only:
            continue
        try:
            raw[iid] = load(os.path.join(INST_DIR, f))
        except ValueError as e:
            qa_extra["invalid_json"].append(f"{f}: {e}")

    db = OrderedDict([(k, []) for k in ("institutions", "sources", "metrics", "partners", "initiatives",
                                         "corrections", "discrepancies", "open_items")])
    for iid, d in raw.items():
        name = d.get("name")
        local_sources = {s.get("id") for s in d.get("sources") or []}

        def check_refs(obj, path):
            if isinstance(obj, dict):
                for k, v in obj.items():
                    if k == "source_ids" and isinstance(v, list):
                        for s in v:
                            if s not in local_sources:
                                qa_extra["broken_source_refs"].append(f"{iid} {path}: {s}")
                    else:
                        check_refs(v, f"{path}.{k}" if path else k)
            elif isinstance(obj, list):
                for n, v in enumerate(obj):
                    check_refs(v, f"{path}[{n}]")
        check_refs({k: v for k, v in d.items() if k != "sources"}, "")
        vocab_check(iid, d, qa_extra["vocabulary_errors"])

        metrics = [enrich_metric(iid, name, n, m, fx, numcheck) for n, m in enumerate(d.get("metrics") or [], 1)]
        kpi = OrderedDict()
        for m in metrics:
            if m["metric"] not in kpi:
                pick = pick_kpi(metrics, m["metric"], d.get("category"))
                if pick:
                    kpi[m["metric"]] = kpi_entry(pick)
        for dc in d.get("disclosure_checks") or []:
            if dc.get("metric") and dc["metric"] not in kpi:
                kpi[dc["metric"]] = OrderedDict([("disclosure", dc.get("status")),
                                                 ("where_checked", dc.get("where_checked"))])
        people = []
        for n, p in enumerate(d.get("people") or [], 1):
            q = OrderedDict([("person_id", f"{iid}:P{n}"), ("institution_id", iid), ("institution", name),
                             ("country", d.get("country"))])
            url = p.get("linkedin_url")
            verified = (p.get("linkedin_status") or "").startswith("Verified")
            for k in PERSON_KEYS:
                if k == "linkedin_url":
                    q[k] = url if (verified or not url) else None
                elif k == "linkedin_unverified_candidate":
                    q[k] = url if (url and not verified) else None
                elif k == "source_ids":
                    q[k] = [f"{iid}:{s}" for s in p.get("source_ids") or []]
                else:
                    q[k] = p.get(k)
            q["key_contact"] = bool(set(p.get("functions") or []) & KEY_CONTACT_FUNCTIONS)
            people.append(q)
        # Institution fields and capabilities keep local source ids (S1…); the flat tables carry '<id>:S1'.
        caps = d.get("capabilities") or {}
        rec = OrderedDict((k, d.get(k)) for k in TOP_COPY)
        rec["country_name"] = COUNTRY_NAMES.get(d.get("country"), d.get("country"))
        rec["kpi"] = kpi
        rec["capabilities"] = caps
        rec["people"] = people
        rec["in_original_workbook"] = iid in original_ids
        partners = [OrderedDict([("institution_id", iid), ("institution", name)] + list(prefixed(p, iid).items()))
                    for p in caps.get("partners") or []]
        initiatives = [OrderedDict([("institution_id", iid), ("institution", name)] + list(prefixed(p, iid).items()))
                       for p in caps.get("initiatives") or []]
        rec["size_band"] = size_band(rec)
        rec["score"] = score(rec, rels.get(iid), partners, initiatives)
        rec["counts"] = OrderedDict([("people", len(people)), ("metrics", len(metrics)),
                                     ("sources", len(d.get("sources") or [])),
                                     ("verified_people", sum(1 for p in people
                                                             if p["role_status"] == "Verified current"))])
        db["institutions"].append(rec)
        for s in d.get("sources") or []:
            lk = links.get(s.get("url")) if s.get("url") else None
            db["sources"].append(OrderedDict([
                ("source_id", f"{iid}:{s.get('id')}"), ("institution_id", iid), ("local_id", s.get("id")),
                ("title", s.get("title")), ("publisher", s.get("publisher")), ("url", s.get("url")),
                ("doc_type", s.get("doc_type")), ("tier", s.get("tier")), ("published", s.get("published")),
                ("accessed", s.get("accessed")), ("language", s.get("language")),
                ("link_state", lk["state"] if lk else None), ("link_code", lk.get("code") if lk else None)]))
        db["metrics"].extend(metrics)
        db["partners"].extend(partners)
        db["initiatives"].extend(initiatives)
        for c in d.get("original_reconciliation") or []:
            db["corrections"].append(OrderedDict(
                [("institution_id", iid), ("institution", name)] +
                [(k, c.get(k)) for k in ("field", "original_value", "finding", "new_value", "materiality")] +
                [("source_ids", [f"{iid}:{s}" for s in c.get("source_ids") or []])]))
        for c in d.get("discrepancies") or []:
            db["discrepancies"].append(OrderedDict(
                [("institution_id", iid), ("institution", name)] +
                [(k, c.get(k)) for k in ("field", "detail", "resolution")] +
                [("source_ids", [f"{iid}:{s}" for s in c.get("source_ids") or []])]))
        for o in d.get("open_items") or []:
            db["open_items"].append(OrderedDict([("institution_id", iid), ("institution", name), ("item", o)]))

    planned = [i for ids in universe["batches"].values() for i in ids]
    meta = OrderedDict([
        ("generated", dt.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")), ("as_of", AS_OF),
        ("standard_balance_sheet_date", STD_BS), ("standard_income_period", "FY2025"), ("fx", fx),
        ("weights", WEIGHTS), ("universe", universe),
        ("counts", OrderedDict([
            ("institutions", len(db["institutions"])),
            ("people", sum(len(i["people"]) for i in db["institutions"])),
            ("metrics", len(db["metrics"])), ("sources", len(db["sources"])),
            ("unique_source_urls", len({s["url"] for s in db["sources"] if s["url"]})),
            ("partners", len(db["partners"])), ("initiatives", len(db["initiatives"])),
            ("planned_institutions", len(planned))])),
        ("structural_corrections", load(os.path.join(RESEARCH, "structural_corrections.json"), [])),
        ("cap_fields", CAP_FIELDS), ("cap_labels", CAP_LABELS),
        ("relationship", OrderedDict((k, v) for k, v in rels.items()))])
    out = OrderedDict([("meta", meta)])
    out.update(db)
    qa = qa_report(out, universe, raw, qa_extra, links)
    return out, qa


def vocab_check(iid, d, errs):
    def chk(field, val, voc):
        if val not in VOCAB[voc]:
            errs.append(f"{iid} {field}: {val!r}")
    for f in ("category", "type", "model", "country", "research_status"):
        chk(f, d.get(f), f)
    for n, m in enumerate(d.get("metrics") or [], 1):
        chk(f"M{n}.status", m.get("status"), "metric_status")
        chk(f"M{n}.period_type", m.get("period_type"), "period_type")
    for dc in d.get("disclosure_checks") or []:
        chk(f"disclosure {dc.get('metric')}", dc.get("status"), "disclosure_status")
    for n, p in enumerate(d.get("people") or [], 1):
        chk(f"P{n}.role_status", p.get("role_status"), "role_status")
        chk(f"P{n}.linkedin_status", p.get("linkedin_status"), "linkedin_status")
        for fn in p.get("functions") or []:
            chk(f"P{n}.functions", fn, "functions")
    caps = d.get("capabilities") or {}
    for f in CAP_FIELDS:
        chk(f"capabilities.{f}", (caps.get(f) or {}).get("present"), "present")
    for p in caps.get("partners") or []:
        chk(f"partner {p.get('partner')}", p.get("status"), "partner_status")


def qa_report(db, universe, raw, extra, links):
    insts = db["institutions"]
    byid = {i["id"]: i for i in insts}
    mbyid = {m["metric_id"]: m for m in db["metrics"]}
    q = OrderedDict()
    q["role_not_verified_current"] = [f"{i['id']} {p['name']}: {p['role_status']}" for i in insts
                                      for p in i["people"] if p["role_status"] != "Verified current"]
    q["number_not_found_in_source"] = [
        f"{m['metric_id']} {m['metric']} {m['value']} {m['unit']} {m['currency'] or ''} {m['period_label']}"
        for m in db["metrics"] if m["auto_check"] == "not_found"]
    q["aum_substitution_risk"] = [f"{m['institution_id']} {m['metric']}: {m['definition']}" for m in db["metrics"]
                                  if m["metric"] in ("aum", "wealth_client_assets")
                                  and AUM_SUBSTITUTION.search(m["definition"] or "")]
    q["linkedin_unverified_candidate_hidden"] = [f"{i['id']} {p['name']}" for i in insts for p in i["people"]
                                                 if p["linkedin_unverified_candidate"]]
    # ASSUMED threshold: fewer than 5 people (18:40 data: 3 flagged, 5 not)
    q["thin_people"] = [f"{i['id']}: {len(i['people'])} people" for i in insts if len(i["people"]) < 5]
    src_local = {s["source_id"]: s for s in db["sources"]}
    q["broken_links"] = [f"{s['institution_id']} {s['local_id']} {s['link_code']} {s['url']}"
                         for s in src_local.values() if s["link_state"] == "broken"]
    q["kpi_not_at_standard_date"] = [f"{i['id']} {k} @ {i['kpi'][k]['period_end']}" for i in insts for k in BS_KPI
                                     if k in i["kpi"] and "metric_id" in i["kpi"][k]
                                     and not i["kpi"][k]["standard_period"]]
    q["fx_missing"] = [f"{m['institution_id']} {m['metric']} {m['currency']} ({m['fx_basis']})" for m in db["metrics"]
                       if m["currency"] and m["unit"] != "percent" and m["fx_rate_per_usd"] is None]
    q["metric_undated"] = [f"{m['institution_id']} {m['metric']}: {m['period_label']}" for m in db["metrics"]
                           if not m["period_end"]]
    q["kpi_not_at_standard_period"] = [f"{i['id']} {k} @ {i['kpi'][k]['period_label']}" for i in insts
                                       for k in ("operating_income", "net_profit")
                                       if k in i["kpi"] and "metric_id" in i["kpi"][k]
                                       and not i["kpi"][k]["standard_period"]]
    # Needs research/original_extracts/ (not transferred to the cloud session): carry the 18:40 results forward.
    carry = load(os.path.join(RESEARCH, "original_value_match_1840.json"), [])
    q["original_value_match"] = [x for x in carry if x.split(" ")[0] in byid] + [
        f"{iid}: not compared (original extract not available in this session)"
        for iid in byid if byid[iid]["in_original_workbook"] and not any(x.startswith(iid + " ") for x in carry)]
    q["sanity_profit_gt_income"] = [
        i["id"] for i in insts
        if (i["kpi"].get("net_profit") or {}).get("value_abs") is not None
        and (i["kpi"].get("operating_income") or {}).get("value_abs") is not None
        and i["kpi"]["net_profit"]["value_abs"] > i["kpi"]["operating_income"]["value_abs"]]
    planned = [i for ids in universe["batches"].values() for i in ids]
    files = {f[:-5] for f in os.listdir(INST_DIR) if f.endswith(".json")}
    q["not_yet_researched"] = sorted(i for i in planned if i not in files)
    q["unplanned_files"] = sorted(files - set(planned))
    names = {}
    for i in insts:
        names.setdefault((i["name"] or "").strip().lower(), []).append(i["id"])
    q["duplicate_institution_names"] = [f"{n}: {sorted(v)}" for n, v in names.items() if len(v) > 1]
    related = {frozenset((i["id"], i["parent_id"])) for i in insts if i.get("parent_id")}
    seen = OrderedDict()
    for i in insts:
        for p in i["people"]:
            if p["role_status"] == "Departed":
                continue
            key = re.sub(r"\s+", " ", (p["name"] or "").strip().lower())
            if i["id"] not in seen.setdefault(key, []):
                seen[key].append(i["id"])
    multi, shared = [], []
    for key, ids in seen.items():
        if len(ids) < 2:
            continue
        ids = sorted(ids)
        all_related = all(any(frozenset((a, b)) in related for b in ids if b != a) for a in ids)
        (shared if all_related else multi).append(f"{key}: {ids}")
    q["people_at_multiple_institutions"] = multi
    q["people_shared_parent_subsidiary"] = shared
    for k, v in extra.items():
        q[k] = v
    accepted = load(os.path.join(RESEARCH, "qa_accepted.json"), [])
    done = []
    for a in accepted:
        lst = q.get(a["check"])
        if not lst:
            continue
        hits = [x for x in lst if x.startswith(a["item_prefix"])]
        for x in hits:
            lst.remove(x)
            done.append(f"{a['check']}: {x} — {a['reason']}")
    q["accepted_after_review"] = done
    return q


# ---------------------------------------------------------------- exports
def cell(v):
    if isinstance(v, list):
        return ";".join(str(x) for x in v)
    return v


def tables(db):
    t = OrderedDict()
    rows = []
    for i in db["institutions"]:
        r = OrderedDict((k, i.get(k)) for k in ("id", "name", "short_name", "legal_name", "name_ar", "country",
                                                 "country_name", "hq_city", "category", "type", "model", "listed",
                                                 "exchange", "ticker", "parent_id", "website", "ownership_summary",
                                                 "government_link", "size_band"))
        for k in ("total_assets", "customer_deposits", "net_loans", "operating_income", "net_profit", "aum", "aua"):
            v = i["kpi"].get(k) or {}
            r[f"{k}_usd_bn"] = v.get("usd_bn")
            r[f"{k}_period"] = v.get("period_label") if "metric_id" in v else v.get("disclosure")
        v = i["kpi"].get("customers") or {}
        r["customers"] = v.get("value_abs")
        r["customers_period"] = v.get("period_label") if "metric_id" in v else v.get("disclosure")
        r["arta_score"] = i["score"]["total"]
        r["arta_tier"] = i["score"]["tier"]
        r["people"] = i["counts"]["people"]
        r["sources"] = i["counts"]["sources"]
        r["research_status"] = i["research_status"]
        rows.append(r)
    t["institutions"] = rows
    t["people"] = [p for i in db["institutions"] for p in i["people"]]
    t["metrics"] = db["metrics"]
    t["sources"] = db["sources"]
    caps = []
    for i in db["institutions"]:
        c = i["capabilities"]
        r = OrderedDict([("institution_id", i["id"]), ("institution", i["name"]), ("country", i["country"]),
                         ("category", i["category"])])
        for f in CAP_FIELDS:
            x = c.get(f) or {}
            r[f] = x.get("present")
            r[f"{f}_detail"] = x.get("detail")
            r[f"{f}_sources"] = [f"{i['id']}:{s}" for s in x.get("source_ids") or []]
        r["asset_classes"] = "; ".join(c.get("asset_classes") or [])
        caps.append(r)
    t["capabilities"] = caps
    for k in ("partners", "initiatives", "corrections", "discrepancies", "open_items"):
        t[k] = db[k]
    return t


def write_all(db, qa, out):
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, "database.json"), "w", encoding="utf-8") as fh:
        json.dump(db, fh, ensure_ascii=False, indent=1)
    with open(os.path.join(out, "qa_report.json"), "w", encoding="utf-8") as fh:
        json.dump(qa, fh, ensure_ascii=False, indent=1)
    t = tables(db)
    sq = os.path.join(out, "gcc_fi.sqlite")
    if os.path.exists(sq):
        os.remove(sq)
    con = sqlite3.connect(sq)
    for name, rows in t.items():
        cols = list(rows[0].keys()) if rows else []
        with open(os.path.join(out, f"{name}.csv"), "w", encoding="utf-8-sig", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(cols)
            for r in rows:
                w.writerow(["" if r.get(c) is None else cell(r.get(c)) for c in cols])
        if cols:
            con.execute(f'CREATE TABLE {name} ({", ".join(chr(34) + c + chr(34) for c in cols)})')
            con.executemany(f'INSERT INTO {name} VALUES ({", ".join("?" for _ in cols)})',
                            [[cell(r.get(c)) for c in cols] for r in rows])
    con.commit()
    con.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=EXPORTS)
    ap.add_argument("--only")
    a = ap.parse_args()
    only = None
    if a.only:
        only = set(open(a.only[1:]).read().split()) if a.only.startswith("@") else set(a.only.split(","))
    db, qa = build(only)
    write_all(db, qa, a.out)
    c = db["meta"]["counts"]
    print(f"Built {c['institutions']} institutions · {c['people']} people · {c['metrics']} metrics · "
          f"{c['sources']} sources → {a.out}")
    for k in ("invalid_json", "broken_source_refs", "vocabulary_errors"):
        print(f"  {k}: {len(qa[k])}")
    print("  QA: " + ", ".join(f"{k} {len(v)}" for k, v in qa.items() if v and k not in
                                ("invalid_json", "broken_source_refs", "vocabulary_errors")))


if __name__ == "__main__":
    sys.exit(main())
