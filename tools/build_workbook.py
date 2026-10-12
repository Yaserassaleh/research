#!/usr/bin/env python3
"""Build the enriched Excel workbook from exports/database.json and exports/qa_report.json.

Writes 'ARTA GCC FI Database (<as_of>).xlsx' in the project folder: 16 sheets (Read me, Institutions, Financials,
Executives, Capabilities, Partners & initiatives, ARTA priorities with live weights, Coverage, Correction log,
Discrepancies & open items, Source register, Data dictionary, FX rates, Universe & exclusions, QA checks,
Relationship contacts (internal)).

The internal relationship sheet is not part of the database: its rows are carried over from the newest existing
workbook in the project folder, so business emails and mailbox links are never written to exports or the site.

Rebuilt on 12 Oct 2026 in the cloud session (the original script was not transferred) to the layout of the
workbook it produced at the pilot stage.
"""
import glob
import json
import os
import sys

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.table import Table, TableStyleInfo

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(ROOT, "exports", "database.json")
QA = os.path.join(ROOT, "exports", "qa_report.json")

INK, MUTED, ACCENT, ACCENT_SOFT = "1C1B2E", "6E6C84", "4A3FC4", "EBE9FB"
OK, WARN, BAD, NA = "E3F3EA", "FBF0DC", "FBE7E5", "EEEDF3"
STATUS_FILL = {
    "Verified": OK, "Verified current": OK, "Complete": OK, "Yes": OK, "Live": OK,
    "Requires verification": WARN, "Unclear": WARN, "Partial": WARN, "Announced": WARN, "MoU / pilot": WARN,
    "Conflicting sources": BAD, "Departed": BAD, "Ended": BAD,
    "Not found after research": NA, "Not publicly disclosed": NA, "No": NA,
}
MARKET = {"AE": "UAE", "SA": "Saudi Arabia", "QA": "Qatar", "KW": "Kuwait", "BH": "Bahrain", "OM": "Oman"}
COMP_LABELS = [("wealth", "Wealth franchise"), ("scale", "Scale"), ("gap", "Digital-investing gap"),
               ("momentum", "Momentum"), ("shelf", "Product-shelf fit"), ("access", "Access & relationship")]
BODY = Font(name="Calibri", size=10)
LINK = Font(name="Calibri", size=10, color=ACCENT)
MAX_CELL = 32000

DATA_DICTIONARY = [
    ("Institutions", "ID", "Stable key: ISO-2 market code + slug (e.g. ae-enbd). Used in file names and all references."),
    ("Institutions", "Category", "Bank · Bank-owned investment subsidiary · Non-bank · International bank (GCC operations). See Universe & exclusions."),
    ("Institutions", "Type", "Universal / commercial bank · Islamic commercial bank · Digital bank · Private / investment bank · Wholesale bank · Asset & wealth manager · Brokerage / investment platform · Digital wealth platform · Investment bank / alternatives manager · Diversified finance company."),
    ("Institutions", "Banking model", "Conventional · Islamic · Conventional with Islamic window/subsidiary · Not applicable."),
    ("Institutions", "Total assets (USD bn)", "Consolidated total assets at the standard balance-sheet date unless the period column says otherwise, converted at the FX rates sheet."),
    ("Institutions", "Customer deposits (USD bn)", "Customer deposits / depositors' accounts as labelled by the issuer; excludes due to banks unless the definition says otherwise."),
    ("Institutions", "Net loans (USD bn)", "Net loans and advances / net financing to customers as labelled; see the definition in Financials."),
    ("Institutions", "Operating income (USD bn)", "Total operating income / net operating income / total revenue as labelled, FY2025 unless stated."),
    ("Institutions", "Net profit (USD bn)", "Net profit attributable to equity holders of the parent, FY2025 unless stated."),
    ("Institutions", "AUM / AUA (USD bn)", "Only when the institution labels it AUM / AUA; otherwise 'Not publicly disclosed' or 'Not found after research'."),
    ("Institutions", "Size band", "Banks by total assets USD: Mega ≥150bn, Large 50–150bn, Mid 15–50bn, Small <15bn. Non-banks by AUM/AUA."),
    ("Institutions", "ARTA score / tier", "Default-weight screening score 0–100 (see ARTA priorities). Tier 1 ≥65, Tier 2 ≥50."),
    ("Financials", "Reported value / Unit / Currency", "As printed in the source (unit = unit, thousand, million or billion) in original currency."),
    ("Financials", "USD bn", "Absolute value ÷ FX per USD ÷ 1e9. Counts (customers, employees) and percentages are not converted."),
    ("Financials", "FX basis", "Peg, or CBK rate at period end (balance sheet) / period average (income) for KWD."),
    ("Financials", "Period end / Period / Period type", "ISO period end; label (e.g. 30 Jun 2026, FY2025, H1 2026); point_in_time or duration."),
    ("Financials", "Standard period?", "Yes if balance-sheet item at 2026-06-30 or income item for FY2025."),
    ("Financials", "Scope", "Group consolidated · Bank standalone · Subsidiary: name · Segment: name."),
    ("Financials", "Status", "Verified · Conflicting sources · Requires verification."),
    ("Financials", "Locator", "Page, note or section in the source where the figure appears."),
    ("Financials", "Auto check", "Result of tools/verify_numbers.py: found · approximate · derived · not_found · unreadable · not run."),
    ("Executives", "Exact title", "Title as shown on the current official source."),
    ("Executives", "Functions", "Controlled tags: Chair, Board, Group CEO, CEO, Deputy CEO, Retail, Affluent, Private banking, Wealth, Investments / asset management, Brokerage, Digital, Technology, Innovation / partnerships, Strategy, Subsidiary CEO, Finance, Treasury, Corporate / wholesale, Operations, Islamic / Shariah, Other."),
    ("Executives", "Role status", "Verified current (official page and no departure news) · Requires verification · Conflicting sources · Departed."),
    ("Executives", "LinkedIn status", "Verified (official link) · Verified (profile/search match: name + current employer + title) · Not verified · Not checked. URLs are never guessed."),
    ("Executives", "Key ARTA contact role", "Yes if the person's functions include CEO, deputy CEO, retail, affluent, private banking, wealth, investments, brokerage, digital, technology, innovation/partnerships, strategy or subsidiary CEO."),
    ("Capabilities", "Each capability", "Yes · No · Not found after research · Unclear, with detail and sources."),
    ("Partners & initiatives", "Status", "Live · Announced · MoU / pilot · Ended · Unclear. An MoU is not a deployment; vendor logos are not clients."),
    ("Source register", "Tier", "1 audited statements, annual reports, regulatory/exchange filings · 2 official sites, releases, presentations · 3 central banks/regulators · 4 official bios, verified LinkedIn · 5 reputable financial news."),
    ("Source register", "Published / Checked", "Publication date where shown; date the source was opened and checked."),
    ("Source register", "Link check", "Result of tools/check_links.py (ok · blocked · broken · error · unreachable, with HTTP code); 'Not checked' if not run."),
    ("All", "Source IDs", "<institution id>:S<n> — look up in Source register."),
]


def yn(v):
    return "Yes" if v is True else "No" if v is False else v


def clip(v):
    if isinstance(v, str) and len(v) > MAX_CELL:
        return v[:MAX_CELL] + " … [truncated; see exports]"
    return v


class Sheet:
    def __init__(self, wb, title, heading, subtitle, first=False):
        self.ws = wb.active if first else wb.create_sheet()
        self.ws.title = title
        self.ws["A1"] = heading
        self.ws["A1"].font = Font(name="Calibri", size=15, bold=True, color=INK)
        if subtitle:
            self.ws["A2"] = subtitle
            self.ws["A2"].font = Font(name="Calibri", size=10, italic=True, color=MUTED)

    def table(self, header, rows, widths, wrap=(), numfmt=None, links=(), fills=(), header_row=4, name=None,
              freeze="B5", as_table=True, bold_cols=()):
        ws = self.ws
        numfmt = numfmt or {}
        for c, h in enumerate(header, 1):
            cell = ws.cell(row=header_row, column=c, value=h)
            cell.font = Font(name="Calibri", size=10, bold=True, color="FFFFFF")
            cell.fill = PatternFill("solid", fgColor=INK)
            cell.alignment = Alignment(wrap_text=True, vertical="top")
        ws.row_dimensions[header_row].height = 30
        r = header_row
        for r, row in enumerate(rows, header_row + 1):
            for c, v in enumerate(row, 1):
                if v is None or v == "":
                    continue
                cell = ws.cell(row=r, column=c, value=clip(v))
                cell.font = Font(name="Calibri", size=10, bold=True) if c in bold_cols else BODY
                if c in wrap:
                    cell.alignment = Alignment(wrap_text=True, vertical="top")
                if c in numfmt and isinstance(v, (int, float)) and not isinstance(v, bool):
                    cell.number_format = numfmt[c]
                if c in links and isinstance(v, str) and v.startswith("http"):
                    cell.hyperlink = v
                    cell.font = LINK
                if c in fills and isinstance(v, str) and v in STATUS_FILL:
                    cell.fill = PatternFill("solid", fgColor=STATUS_FILL[v])
        for c, w in enumerate(widths, 1):
            ws.column_dimensions[get_column_letter(c)].width = w
        if freeze:
            ws.freeze_panes = freeze
        last = max(r, header_row + 1)
        ref = f"A{header_row}:{get_column_letter(len(header))}{last}"
        if as_table:
            t = Table(displayName=name or "t_" + "".join(ch for ch in ws.title if ch.isalnum()), ref=ref)
            t.tableStyleInfo = TableStyleInfo(name="TableStyleLight1", showRowStripes=True)
            ws.add_table(t)
        return ref


def kv(i, k):
    v = i["kpi"].get(k)
    if not v:
        return None, None
    if "disclosure" in v:
        return v["disclosure"], v["disclosure"]
    return v.get("usd_bn"), v.get("period_label")


def relationship_rows():
    files = sorted(glob.glob(os.path.join(ROOT, "ARTA GCC FI Database (*).xlsx")), key=os.path.getmtime, reverse=True)
    for f in files:
        try:
            wb = load_workbook(f)
        except Exception:
            continue
        name = next((n for n in wb.sheetnames if n.startswith("Relationship contacts")), None)
        if not name:
            continue
        ws = wb[name]
        rows = [list(r) for r in ws.iter_rows(min_row=5, values_only=True) if any(v is not None for v in r)]
        return rows, os.path.basename(f)
    return [], None


def main():
    db = json.load(open(DB, encoding="utf-8"))
    qa = json.load(open(QA, encoding="utf-8"))
    meta, insts = db["meta"], db["institutions"]
    as_of = meta["as_of"]
    out = os.path.join(ROOT, f"ARTA GCC FI Database ({as_of}).xlsx")
    rel_rows, rel_from = relationship_rows()
    c = meta["counts"]
    wb = Workbook()

    # Read me
    s = Sheet(wb, "Read me", "ARTA GCC Financial Institutions Database",
              f"Phase 1 research foundation · data as of {as_of} · generated {meta['generated']}", first=True)
    ws = s.ws
    ws["A2"].alignment = Alignment(wrap_text=True, vertical="top")
    lines = [
        (4, "What this is", True),
        (5, f"A verified database of {c['institutions']} GCC banks, bank-owned capital-market arms, non-bank "
            f"wealth/investment firms and international banks' GCC operations, with {c['people']} executives, "
            f"{c['metrics']} dated financial data points and {c['sources']} cited sources. Built for ARTA's partnerships "
            f"team (Wissam, Hani) for partner research, account planning and meeting preparation. "
            f"{c['institutions']} of {c['planned_institutions']} planned institutions are researched; see Coverage.", False),
        (7, "How to use the sheets", True),
        (8, "Institutions — one row per institution; USD figures at the standard dates; filter by market, category, model, size band or tier.", False),
        (9, "Financials — every data point with value, unit, original currency, USD, period, scope, definition, status, page locator and source.", False),
        (10, "Executives — leadership and decision-makers; role status, appointment date, career, education, LinkedIn verification status, sources.", False),
        (11, "Capabilities — wealth, brokerage, asset management, digital investing, advisory/discretionary, model portfolios, structured products, private markets, Islamic wealth: Yes / No / Not found / Unclear, with detail and sources.", False),
        (12, "Partners & initiatives — named technology/product partners and dated launches, acquisitions and strategy moves.", False),
        (13, "ARTA priorities — transparent partner-fit score. Change the weights in row 5 of that sheet; scores and tiers recalculate.", False),
        (14, "Coverage — completed vs outstanding institutions, field availability, unavailable fields. Correction log — every material change to the 7 Oct 2026 workbook. Discrepancies & open items — unresolved conflicts and next checks.", False),
        (15, "Source register — every source with tier, document type, publication date and date checked. Data dictionary — every field defined. FX rates — the conversion basis.", False),
        (17, "Reading the data", True),
        (18, "Standard comparison dates: balance sheet at 2026-06-30 (H1 2026); income for FY2025. A figure at another date is flagged and should not be compared directly.", False),
        (19, "USD conversion: AED 3.6725, SAR 3.75, QAR 3.64, BHD 0.376, OMR 0.3845 per USD (official pegs). KWD at the Central Bank of Kuwait rate for the period (period-end for balance sheet; period average for income).", False),
        (20, "AUM is never inferred from total assets, deposits, custody or fiduciary assets. If an institution does not publish AUM, the database says 'Not publicly disclosed' and records where we looked.", False),
        (21, "Status values: Verified · Requires verification · Conflicting sources · Not publicly disclosed · Not found after research. People: Verified current · Requires verification · Conflicting sources · Departed.", False),
        (22, "Group figures include subsidiaries profiled separately (e.g. Emirates Islamic inside Emirates NBD; Kamco inside Burgan). Do not add parent and subsidiary figures together.", False),
        (23, "The ARTA score is a screening aid computed only from evidence in the profiles. It is not a recommendation; flags (Islamic shelf, KSA licensing, competing product) are listed but not scored.", False),
        (25, "Refreshing", True),
        (26, "1. Each institution is one JSON file in research/institutions/, written to research/RESEARCH_PROTOCOL.md.  2. Edit or add files with sourced, dated values.  3. Run: python3 tools/build_db.py  →  python3 tools/build_workbook.py  →  python3 tools/build_site.py.  4. Republish the website from site/gcc-fi-intelligence.html.  5. Twice a year roll the standard dates forward and re-check leadership pages.", False),
        (27, "Machine-readable exports: exports/database.json (full), exports/*.csv (one per table), exports/gcc_fi.sqlite. QA results: exports/qa_report.json.", False),
        (28, "The original workbook is preserved unchanged in '00 Original workbook (unchanged)'.", False),
        (30, "Internal data", True),
        (31, "The sheet 'Relationship contacts (internal)' carries prior-correspondence contacts and internal links from the original workbook. It is not included in the website or exports.", False),
    ]
    for r, text, head in lines:
        cell = ws.cell(row=r, column=1, value=text)
        cell.font = Font(size=12, bold=True, color=INK) if head else BODY
        cell.alignment = Alignment(wrap_text=True, vertical="top")
    ws.column_dimensions["A"].width = 150

    # Institutions
    s = Sheet(wb, "Institutions", "Institutions",
              "USD at standard dates: balance sheet 2026-06-30, income FY2025. Period columns show any exception.")
    header = ["ID", "Institution", "Short name", "Legal name", "Arabic name", "Market", "HQ city", "Category", "Type",
              "Banking model", "Listed", "Exchange", "Ticker", "Parent (profiled)", "Website",
              "Total assets (USD bn)", "Assets period", "Customer deposits (USD bn)", "Deposits period",
              "Net loans (USD bn)", "Loans period", "Operating income (USD bn)", "Op. income period",
              "Net profit (USD bn)", "Net profit period", "AUM (USD bn)", "AUM period / status", "AUA (USD bn)",
              "AUA period / status", "Customers", "Customers period", "Size band", "Ownership", "Government link",
              "ARTA score (default)", "ARTA tier (default)", "People", "People verified current", "Sources",
              "Research status", "In original workbook", "Checked"]
    rows = []
    for i in insts:
        row = [i["id"], i["name"], i["short_name"], i["legal_name"], i["name_ar"], MARKET.get(i["country"]),
               i["hq_city"], i["category"], i["type"], i["model"], yn(i["listed"]), i["exchange"], i["ticker"],
               i["parent_id"], i["website"]]
        for k in ("total_assets", "customer_deposits", "net_loans", "operating_income", "net_profit", "aum", "aua"):
            row += list(kv(i, k))
        cu = i["kpi"].get("customers") or {}
        row += [cu.get("disclosure") if "disclosure" in cu else cu.get("value_abs"),
                cu.get("disclosure") if "disclosure" in cu else cu.get("period_label")]
        row += [i["size_band"], i["ownership_summary"], i["government_link"], i["score"]["total"],
                i["score"]["tier"], i["counts"]["people"], i["counts"]["verified_people"], i["counts"]["sources"],
                i["research_status"], yn(i["in_original_workbook"]), i["checked"]]
        rows.append(row)
    s.table(header, rows, [12, 30, 12, 30, 22, 12, 12, 22, 24, 22, 7, 9, 13, 20, 28] + [11, 12] * 8 +
            [14, 18, 50, 36, 9, 9, 8, 9, 8, 11, 9],
            wrap={2, 4, 33, 34}, links={15},
            numfmt={16: "#,##0.0", 18: "#,##0.0", 20: "#,##0.0", 22: "#,##0.0", 24: "#,##0.0", 26: "#,##0.0",
                    28: "#,##0.0", 30: "#,##0"}, fills={40})

    # Financials
    s = Sheet(wb, "Financials", "Financial data points",
              "One row per data point. Values in original currency and unit as reported; USD computed with the FX rates sheet.")
    header = ["Metric ID", "Institution ID", "Institution", "Metric", "Reported value", "Unit", "Currency",
              "Value (absolute)", "USD bn", "FX per USD", "FX basis", "Period end", "Period", "Period type",
              "Standard period?", "Scope", "Definition", "Status", "Locator", "Note", "Source IDs", "Auto check"]
    rows = [[m["metric_id"], m["institution_id"], m["institution"], m["metric"], m["value"], m["unit"], m["currency"],
             m["value_abs"], m["usd_bn"], m["fx_rate_per_usd"], m["fx_basis"], m["period_end"], m["period_label"],
             m["period_type"], yn(m["standard_period"]), m["scope"], m["definition"], m["status"], m["locator"],
             m["note"], "; ".join(m["source_ids"]), m["auto_check"]] for m in db["metrics"]]
    s.table(header, rows, [16, 14, 26, 18, 14, 9, 8, 16, 10, 9, 22, 11, 14, 12, 9, 22, 46, 14, 18, 30, 26, 12],
            wrap={17, 20, 21}, numfmt={8: "#,##0", 9: "#,##0.000"}, fills={18})

    # Executives
    s = Sheet(wb, "Executives", "Executives and decision-makers",
              "Professional information only. LinkedIn URLs only where linked officially or matched on name, current employer and title.")
    header = ["Person ID", "Institution ID", "Institution", "Market", "Name", "Arabic name", "Exact title",
              "Functions", "Entity", "Business unit", "Scope", "Appointed", "Appointment note",
              "Career / previous roles", "Education", "Qualifications", "LinkedIn URL", "LinkedIn status",
              "Role status", "Role evidence", "Key ARTA contact role", "Source IDs", "Checked"]
    rows = [[p["person_id"], i["id"], i["name"], MARKET.get(i["country"]), p["name"], p["name_ar"], p["title"],
             "; ".join(p["functions"] or []), p["entity"], p["business_unit"], p["scope"], p["appointed"],
             p["appointed_note"], p["previous_roles"], p["education"], p["qualifications"], p["linkedin_url"],
             p["linkedin_status"], p["role_status"], p["role_evidence"], yn(p["key_contact"]),
             "; ".join(p["source_ids"]), p["checked"]] for i in insts for p in i["people"]]
    s.table(header, rows, [14, 13, 24, 10, 24, 18, 36, 22, 22, 18, 12, 11, 22, 60, 30, 16, 30, 18, 16, 40, 9, 22, 11],
            wrap={7, 8, 13, 14, 15, 20}, links={17}, fills={19})

    # Capabilities
    s = Sheet(wb, "Capabilities", "Wealth, investment and digital capabilities",
              "Yes = evidenced; No = evidenced absence; Not found after research = no evidence located (not proof of absence); Unclear = mixed evidence.")
    fields, labels = meta["cap_fields"], meta["cap_labels"]
    header = ["Institution ID", "Institution", "Market", "Category", "Wealth summary"] + [labels[f] for f in fields] + \
             ["Asset classes"] + [f"{labels[f]} — detail" for f in fields]
    rows = []
    for i in insts:
        cap = i["capabilities"]
        det = []
        for f in fields:
            x = cap.get(f) or {}
            src = "; ".join(f"{i['id']}:{s_}" for s_ in x.get("source_ids") or [])
            det.append((x.get("detail") or "") + (f" [{src}]" if src else ""))
        rows.append([i["id"], i["name"], MARKET.get(i["country"]), i["category"], cap.get("wealth_summary")] +
                    [(cap.get(f) or {}).get("present") for f in fields] + ["; ".join(cap.get("asset_classes") or [])] +
                    det)
    s.table(header, rows, [13, 26, 10, 18, 60] + [12] * len(fields) + [36] + [44] * len(fields),
            wrap={5, 17} | set(range(18, 18 + len(fields))), fills=set(range(6, 6 + len(fields))))

    # Partners & initiatives
    s = Sheet(wb, "Partners & initiatives", "Named partners and dated initiatives",
              "Technology, product and distribution partners; launches, acquisitions and strategy statements. MoUs are not treated as deployments.")
    rows = [["Partner", p["institution_id"], p["institution"], p.get("date"), p.get("partner"), p.get("kind"),
             p.get("what"), p.get("status"), "; ".join(p.get("source_ids") or [])] for p in db["partners"]]
    rows += [["Initiative", p["institution_id"], p["institution"], p.get("date"), None, None, p.get("what"), None,
              "; ".join(p.get("source_ids") or [])] for p in db["initiatives"]]
    s.table(["Kind", "Institution ID", "Institution", "Date", "Partner", "Partner type", "What", "Status",
             "Source IDs"], rows, [11, 14, 26, 11, 24, 22, 70, 12, 26], wrap={5, 7}, fills={8})

    # ARTA priorities (live weights)
    s = Sheet(wb, "ARTA priorities", "ARTA partner-fit screening",
              "Component scores (0–5) come from the evidence in each profile. Change the weights in row 5; Score = Σ(weight × component/5) ÷ Σweights × 100. Tier 1 ≥ 65, Tier 2 ≥ 50.")
    ws = s.ws
    ws["E4"] = "Weights →"
    ws["E4"].font = Font(bold=True, color=ACCENT)
    for n, (k, lab) in enumerate(COMP_LABELS):
        col = get_column_letter(6 + n)
        ws[f"{col}4"] = lab
        ws[f"{col}4"].font = Font(size=9, bold=True, color=MUTED)
        ws[f"{col}5"] = meta["weights"][k]
        ws[f"{col}5"].font = Font(bold=True, color=ACCENT)
        ws[f"{col}5"].fill = PatternFill("solid", fgColor=ACCENT_SOFT)
    header = ["Institution ID", "Institution", "Market", "Category", "Type"] + [l for _, l in COMP_LABELS] + \
             ["Score", "Tier", "Flags (not scored)"] + [f"{l} — why" for _, l in COMP_LABELS]
    ranked = sorted(insts, key=lambda i: -i["score"]["total"])
    rows = []
    for r, i in enumerate(ranked, 8):
        comp = i["score"]["components"]
        rows.append([i["id"], i["name"], MARKET.get(i["country"]), i["category"], i["type"]] +
                    [comp[k]["score"] for k, _ in COMP_LABELS] +
                    [f"=ROUND(SUMPRODUCT($F$5:$K$5,F{r}:K{r})/5/SUM($F$5:$K$5)*100,1)",
                     f'=IF(L{r}>=65,"Tier 1",IF(L{r}>=50,"Tier 2","Tier 3"))',
                     "; ".join(i["score"]["flags"])] + [comp[k]["why"] for k, _ in COMP_LABELS])
    ref = s.table(header, rows, [13, 28, 11, 20, 22, 11, 11, 11, 11, 11, 11, 9, 9, 34, 36, 36, 36, 36, 36, 36],
                  header_row=7, freeze="C8", as_table=False, wrap={14, 15, 16, 17, 18, 19, 20}, bold_cols={12})
    ws.auto_filter.ref = ref

    # Coverage
    researched = {i["id"]: i for i in insts}
    batch_of = {iid: b for b, ids in meta["universe"]["batches"].items() for iid in ids}
    planned = [iid for ids in meta["universe"]["batches"].values() for iid in ids]
    s = Sheet(wb, "Coverage", "Coverage report",
              f"{len(researched)} of {len(planned)} planned institutions researched. 'Not publicly disclosed' = checked and not published; 'Not recorded' = gap to close.")
    cols = ["total_assets", "customer_deposits", "net_loans", "operating_income", "net_profit", "aum", "aua", "customers"]

    def avail(i, k):
        v = i["kpi"].get(k)
        if not v:
            return "Not recorded"
        if "disclosure" in v:
            return v["disclosure"]
        return f"Yes ({v['period_label']})" if v["standard_period"] else f"Other period: {v['period_label']}"
    rows = []
    for i in insts:
        unresolved = sum(1 for f in fields if (i["capabilities"].get(f) or {}).get("present") in
                         ("Unclear", "Not found after research"))
        rows.append([i["id"], i["name"], MARKET.get(i["country"]), i["category"], i["research_status"]] +
                    [avail(i, k) for k in cols] +
                    [i["counts"]["people"], i["counts"]["verified_people"],
                     sum(1 for p in i["people"] if (p["linkedin_status"] or "").startswith("Verified")),
                     i["counts"]["sources"], unresolved])
    for iid in planned:
        if iid not in researched:
            rows.append([iid, meta["universe"]["names"].get(iid), None, None, f"Outstanding (batch {batch_of[iid]})"] +
                        ["Not researched"] * len(cols) + [0, 0, 0, 0, None])
    ws = s.ws
    s.table(["Institution ID", "Institution", "Market", "Category", "Research status", "Total assets", "Deposits",
             "Loans", "Op. income", "Net profit", "AUM", "AUA", "Customers", "People", "Verified current",
             "LinkedIn verified", "Sources", "Capability fields unresolved"], rows,
            [13, 28, 10, 20, 16] + [16] * 8 + [8, 9, 9, 8, 11], wrap=set(range(1, 19)), fills=set(range(5, 14)))

    # Correction log
    s = Sheet(wb, "Correction log", "Correction log against the 7 Oct 2026 workbook",
              "Structural fixes first, then every original field and person reconciled. Findings: Confirmed · Corrected · Updated · Could not verify · Removed.")
    rows = [[None, "Structural", x.get("area"), x.get("item"), x.get("original"), x.get("finding"), x.get("now"),
             x.get("materiality"), None] for x in meta["structural_corrections"]]
    rows += [[x["institution_id"], x["institution"], "Original workbook", x.get("field"), x.get("original_value"),
              x.get("finding"), x.get("new_value"), x.get("materiality"), "; ".join(x.get("source_ids") or [])]
             for x in db["corrections"]]
    s.table(["Institution ID", "Institution", "Area", "Field / item", "Original", "Finding", "Now", "Materiality",
             "Source IDs"], rows, [13, 24, 18, 34, 46, 14, 56, 11, 24], wrap={4, 5, 7}, fills={6})

    # Discrepancies & open items
    s = Sheet(wb, "Discrepancies & open items", "Discrepancies, open items and QA flags",
              "Conflicting sources with both references, what could not be verified, and automated QA flags.")
    rows = [["Discrepancy", x["institution_id"], x["institution"], x.get("field"), x.get("detail"),
             x.get("resolution"), "; ".join(x.get("source_ids") or [])] for x in db["discrepancies"]]
    rows += [["Open item", x["institution_id"], x["institution"], None, x["item"], None, None] for x in db["open_items"]]
    for check, items in qa.items():
        if check in ("not_yet_researched", "original_value_match"):
            continue
        for it in items:
            first = str(it).split(" ")[0].split(":")[0]
            rows.append([f"QA: {check.replace('_', ' ')}", first if first in researched else None, None, None, it,
                         None, None])
    s.table(["Kind", "Institution ID", "Institution", "Field", "Detail", "Resolution", "Source IDs"], rows,
            [22, 14, 24, 22, 80, 46, 24], wrap={5, 6})

    # Source register
    s = Sheet(wb, "Source register", "Source register",
              "Tier 1 audited statements/filings · 2 official sites, releases, presentations · 3 regulators · 4 official bios/verified LinkedIn · 5 reputable news.")
    name_of = {i["id"]: i["name"] for i in insts}
    rows = [[x["source_id"], x["institution_id"], name_of.get(x["institution_id"]), x["title"], x["publisher"],
             x["doc_type"], x["tier"], x["published"], x["accessed"], x["language"],
             (f"{x['link_state']} ({x['link_code']})" if x["link_code"] else x["link_state"]) if x["link_state"]
             else "Not checked", x["url"]] for x in db["sources"]]
    s.table(["Source ID", "Institution ID", "Institution", "Title", "Publisher", "Document type", "Tier", "Published",
             "Checked", "Language", "Link check", "URL"], rows, [18, 13, 24, 50, 24, 24, 6, 11, 11, 8, 14, 60],
            wrap={4}, links={12})

    # Data dictionary
    s = Sheet(wb, "Data dictionary", "Data dictionary",
              "Field definitions for every sheet and export (the CSV/SQLite exports use the same field names in snake_case).")
    s.table(["Sheet / table", "Field", "Definition"], [list(r) for r in DATA_DICTIONARY], [22, 32, 120], wrap={3})

    # FX rates
    fx = meta["fx"]
    s = Sheet(wb, "FX rates", "FX rates (local currency per USD)", fx["note"])
    rows = [[cur, None, v["rate"], v["basis"], v["source"], v["url"]] for cur, v in fx["pegged"].items() if cur != "USD"]
    for d, rate in sorted(fx["KWD"]["point_rates"].items()):
        rows.append(["KWD", d, rate, "CBK daily rate (fils/1000), period end", fx["KWD"]["source"], fx["KWD"]["url"]])
    for p, v in fx["KWD"]["average_rates"].items():
        rows.append(["KWD", p, v["rate"], "Period average (income items)", v["source"], v["url"]])
    s.table(["Currency", "Date / period", "Per USD", "Basis", "Source", "URL"], rows, [10, 14, 10, 40, 70, 60],
            wrap={1, 2, 3, 4, 5, 6}, links={6})

    # Universe & exclusions
    s = Sheet(wb, "Universe & exclusions", "Institution universe and inclusion criteria",
              "Every planned institution, its research status, and names excluded or folded into another record, with reasons.")
    rows = [["Inclusion rule", None, None, r] for r in meta["universe"]["inclusion_criteria"]]
    for iid in planned:
        i = researched.get(iid)
        status = (f"Researched — {i['research_status']} (batch {batch_of[iid]})" if i
                  else f"Outstanding (batch {batch_of[iid]})")
        rows.append(["Planned institution", iid, meta["universe"]["names"].get(iid), status])
    rows += [["Excluded / folded", None, x["name"], x["reason"]] for x in meta["universe"]["excluded_watchlist"]]
    s.table(["Kind", "ID", "Name", "Detail"], rows, [20, 22, 40, 120], wrap={3, 4})

    # QA checks
    s = Sheet(wb, "QA checks", "Automated quality checks",
              "Run by tools/build_db.py on every build. Zero is the target for invalid JSON, broken source references and vocabulary errors.")
    rows = [[k.replace("_", " "), len(v), "; ".join(str(x) for x in v)] for k, v in qa.items()]
    s.table(["Check", "Count", "Items"], rows, [36, 8, 140], wrap={3})

    # Relationship contacts (internal)
    s = Sheet(wb, "Relationship contacts (internal)", "Relationship contacts and internal notes (internal only)",
              "Carried over from the 7 Oct 2026 workbook. Not verified as public facts; excluded from the website and exports."
              + ("" if rel_rows else " (No earlier workbook with this sheet was found at build time.)"))
    s.table(["Origin", "Institution", "Name / item", "Title / value as recorded", "Status as recorded",
             "Evidence date", "Business email (prior correspondence)", "Internal link", "Notes"],
            [r[:9] for r in rel_rows], [26, 22, 26, 34, 26, 12, 30, 40, 50], wrap={4, 5, 8, 9})

    wb.save(out)
    print(f"{os.path.basename(out)}: {len(wb.sheetnames)} sheets, {len(insts)} institutions, "
          f"{len(rel_rows)} internal relationship rows carried over" + (f" from {rel_from}" if rel_from else ""))


if __name__ == "__main__":
    sys.exit(main())
