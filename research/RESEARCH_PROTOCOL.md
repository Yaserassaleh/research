# ARTA GCC FI Intelligence — Research Protocol (v1, 12 Oct 2026)

Every research agent follows this protocol exactly. Output is one JSON file per institution in
`research/institutions/<id>.json`. The database, Excel workbook and website are generated from these files,
so field names, vocabularies and formats must match this document.

## 1. Purpose and users
A source of truth for ARTA's partnerships team (Wissam, Hani) for partner research, account planning and
meeting preparation. ARTA (Arta Finance) sells wealth technology to banks and wealth firms in three ways:
(1) a product shelf by API — model/managed portfolios, alternatives/private markets, structured products;
(2) a white-label digital wealth platform; (3) AI agents for relationship managers and clients.
Live GCC partner: Wio Bank (Wio Invest), UAE. So the evidence that matters is: wealth/affluent/private-banking
franchise, digital investing channels, brokerage/execution, advisory and discretionary services, product shelf,
named technology vendors and product partners, recent wealth/digital launches, stated strategy, and gaps.
Do NOT write sales copy or opinions about ARTA in the files; record evidence. Scoring is done centrally.

## 2. Verification rules (non-negotiable)
- Never fabricate values, titles, biographies, sources or URLs. Every URL you record must be one you actually
  opened (WebFetch) or saw returned by a search tool. If you only saw it in a search result, say so in `note`.
- Cite at field level: every metric, person and capability item carries `source_ids` pointing into `sources`.
- Source hierarchy (record `tier`): 1 audited/reviewed financial statements, annual reports, regulatory filings,
  exchange disclosures (Tadawul, ADX, DFM, QSE, Boursa Kuwait, Bahrain Bourse, MSX); 2 official institution
  website, leadership pages, press releases, investor presentations; 3 central banks and regulators (CBUAE,
  SAMA, CMA, QCB, QFMA, CBK, CMA Kuwait, CBB, CBO, FSA Oman, DFSA, FSRA, SCA); 4 official biographies and
  verified LinkedIn profiles; 5 reputable financial news (Reuters, Bloomberg, Zawya, The National, Arab News,
  Gulf News, Argaam, Al Eqtisadiah, Gulf Business, The Banker, Asian Banker, Finextra, Fintech News ME) — use
  for corroboration or context otherwise unavailable. Avoid aggregators, AI summaries, data brokers, Wikipedia
  (may be used only as a lead, never cited).
- Search in English and Arabic where useful (Arabic names, Argaam, Saudi Exchange Arabic announcements).
- Never substitute total assets, deposits, custody assets, fiduciary assets or investment securities for AUM.
  If AUM is not disclosed, record it in `disclosure_checks` as "Not publicly disclosed" with where you looked.
- Do not label anything "current" without a reporting date and a check date.
- If a page is blocked or unavailable, record the limitation (in `open_items`) and continue.
- Do not solve CAPTCHAs or bypass bot checks. Do not log in anywhere.
- People: professional information only (titles, appointment dates, career, education, professional
  qualifications). No personal contact details, ages, birth dates, family, nationality, religion, photos,
  personal social media. Do not infer undocumented reporting lines.
- LinkedIn: never guess or construct a URL. Record a URL only if (a) the official site links it, or (b) you
  opened the profile or saw a search result whose snippet shows the same name AND the same current employer AND
  a consistent title/career. Otherwise `linkedin_url: null` and status "Not verified". LinkedIn checks cost
  searches — do them for CEO, wealth/private-banking/affluent heads, investments/asset-management/brokerage
  heads, digital/innovation heads. Everyone else: "Not checked".
- Verify each person still holds the role: check the current official leadership page AND search for recent
  appointment/departure news (2025–2026). If the official page and news conflict, use status
  "Conflicting sources" and explain.
- Search budget: WebSearch is rationed (roughly 20 searches per institution). Prefer WebFetch on known official
  URLs (IR pages, leadership pages, exchange disclosure pages) over WebSearch. Do NOT use DuckDuckGo/Bing pages as a
  substitute (they serve challenge pages). If WebSearch stops working, continue from official sources and record
  "News/LinkedIn check not run (search quota)" in open_items for the affected people.
- PDFs: WebFetch can read many PDFs. For large annual reports, use `offset` to page through, or fetch the
  investor presentation / results press release instead. Record page numbers in `locator` when you can.
  For PDFs over 10 MB, or when WebFetch is refused but the file is public, use Bash:
  `PDF_CACHE=/private/tmp/claude-501/gccfi_pdf python3 -E "/Users/yaserassaleh/Library/CloudStorage/OneDrive-beyridge.com/ARTA GCC FI Intelligence/tools/pdftext.py" "<pdf url>" --grep "total assets|customers' deposits" --context 600`
  (prints PDF page numbers; `--pages 1-15` prints whole pages). Sites with bot protection block this too; then
  record the limitation.

## 3. Reporting-date standard (makes comparisons valid)
- Balance-sheet metrics (total assets, customer deposits, loans): primary period = 30 Jun 2026 (H1 2026).
  If not published, use the latest available (31 Mar 2026 or 31 Dec 2025) and say so. If Q3 2026 (30 Sep 2026)
  is already published, ALSO record it as an extra record — but always record 30 Jun 2026 too when available.
- Income metrics (operating income, net profit): primary = FY2025 (12 months to 31 Dec 2025).
  Also record H1 2026 net profit when easily available.
- Non-calendar fiscal years (rare): record exact period dates.
- Record values in ORIGINAL currency and the unit as printed (unit|thousand|million|billion). Do NOT convert
  to USD — conversion is done centrally with documented FX. If the source itself is in USD, record USD.

## 4. Standard metrics (`metric` key → meaning)
| key | definition to state in `definition` |
|---|---|
| total_assets | Total assets, statement of financial position |
| customer_deposits | Customer deposits / depositors' accounts / due to customers — state exact label and exclusions (e.g. excludes due to banks) |
| net_loans | Net loans & advances / net financing to customers — state exact label (net of ECL? includes Islamic financing?) |
| gross_loans | Gross loans/financing (only if clearly labelled) |
| total_equity | Total equity (optional) |
| operating_income | Total operating income / total revenue / net operating income — state exact label |
| net_profit | Net profit attributable to equity holders of the parent (state if it is total net profit instead) |
| aum | Assets under management — only when the issuer labels it AUM; state discretionary/non-discretionary if said |
| aua | Assets under administration / custody — only when labelled |
| wealth_client_assets | Wealth/private-banking client assets/balances when disclosed (state exact label) |
| customers | Number of customers/clients (state retail vs total, active vs registered) |
| investing_users | Number of investment/brokerage/app investing clients if disclosed |
| employees | Headcount (optional) |
| branches | Number of branches (optional) |
Other metrics allowed with a clear snake_case key (e.g. `brokerage_trading_value`, `fund_count`).

## 5. Controlled vocabularies
- `category`: "Bank" | "Bank-owned investment subsidiary" | "Non-bank" | "International bank (GCC operations)"
- `type`: "Universal / commercial bank" | "Islamic commercial bank" | "Digital bank" | "Private / investment bank"
  | "Wholesale bank" | "Asset & wealth manager" | "Brokerage / investment platform" | "Digital wealth platform"
  | "Investment bank / alternatives manager" | "Diversified finance company"
- `model`: "Conventional" | "Islamic" | "Conventional with Islamic window/subsidiary" | "Not applicable"
- `country`: "AE" | "SA" | "QA" | "KW" | "BH" | "OM" (international banks: country where GCC hub is, plus note)
- metric `status`: "Verified" | "Conflicting sources" | "Requires verification"
- disclosure check `status`: "Not publicly disclosed" | "Not found after research"
- person `role_status`: "Verified current" | "Requires verification" | "Conflicting sources" | "Departed"
- `linkedin_status`: "Verified (official link)" | "Verified (profile/search match)" | "Not verified" | "Not checked"
- capability `present`: "Yes" | "No" | "Not found after research" | "Unclear"
- partner `status`: "Live" | "Announced" | "MoU / pilot" | "Ended" | "Unclear"
- person `functions` (one or more): "Chair" | "Board" | "Group CEO" | "CEO" | "Deputy CEO" | "Retail" | "Affluent"
  | "Private banking" | "Wealth" | "Investments / asset management" | "Brokerage" | "Digital" | "Technology"
  | "Innovation / partnerships" | "Strategy" | "Subsidiary CEO" | "Finance" | "Treasury" | "Corporate / wholesale"
  | "Operations" | "Islamic / Shariah" | "Other"

## 6. JSON schema (all keys required; use null / [] when unknown — never omit keys)
```json
{
  "id": "ae-enbd",
  "name": "Emirates NBD",
  "short_name": "ENBD",
  "legal_name": "Emirates NBD Bank P.J.S.C.",
  "name_ar": "بنك الإمارات دبي الوطني",
  "country": "AE",
  "hq_city": "Dubai",
  "website": "https://www.emiratesnbd.com",
  "linkedin_company": "https://www.linkedin.com/company/emirates-nbd/  (only if verified; else null)",
  "category": "Bank",
  "type": "Universal / commercial bank",
  "model": "Conventional with Islamic window/subsidiary",
  "founded": "2007 (merger of Emirates Bank International and National Bank of Dubai)",
  "regulators": ["CBUAE", "SCA"],
  "listed": true,
  "exchange": "DFM",
  "ticker": "EMIRATESNBD",
  "parent_id": null,
  "ownership_summary": "one or two sentences with dates",
  "shareholders": [{"holder": "Investment Corporation of Dubai", "pct": 55.8, "as_of": "2025-12-31", "source_ids": ["S2"]}],
  "government_link": "Yes — ICD, owned by Government of Dubai (as of ...)",
  "group_structure": "short text",
  "subsidiaries": [{"name": "Emirates Islamic Bank PJSC", "pct": 99.9, "activity": "Islamic bank", "linked_id": "ae-ei", "source_ids": ["S2"]}],
  "footprint": "countries / branch network, with date",
  "customer_segments": "retail, affluent, private, SME, corporate ...",
  "business_lines": "specific description of main lines incl. retail, affluent, private banking, wealth, brokerage, asset management",
  "metrics": [
    {"metric": "total_assets", "value": 1322466, "unit": "million", "currency": "AED",
     "period_end": "2026-06-30", "period_label": "30 Jun 2026", "period_type": "point_in_time",
     "scope": "Group consolidated", "definition": "Total assets, condensed consolidated statement of financial position",
     "status": "Verified", "source_ids": ["S3"], "locator": "p.2", "note": ""}
  ],
  "disclosure_checks": [
    {"metric": "aum", "status": "Not publicly disclosed", "where_checked": "FY2025 annual report (S2); H1 2026 results release (S4)"}
  ],
  "people": [
    {"name": "Shayne Nelson", "name_ar": null, "title": "Group Chief Executive Officer",
     "functions": ["Group CEO"], "entity": "Emirates NBD Bank PJSC", "business_unit": "Group", "scope": "Group",
     "appointed": "2013-10", "appointed_note": "",
     "previous_roles": "Chronological, e.g. 2013– Group CEO Emirates NBD; 2008–2013 Standard Chartered ... (from official bio)",
     "education": "e.g. MBA, Melbourne Business School (only if in an official/verified source)",
     "qualifications": null,
     "linkedin_url": null, "linkedin_status": "Not verified",
     "role_status": "Verified current",
     "role_evidence": "Official leadership page, checked 2026-10-12 (S1); no departure news found",
     "source_ids": ["S1"], "checked": "2026-10-12"}
  ],
  "capabilities": {
    "wealth_summary": "3-6 sentences, specific to this institution (named propositions, thresholds, products, vendors, dates).",
    "segments": [{"name": "Priority Banking", "tier": "Affluent", "eligibility": "AED ... relationship balance (as published)", "source_ids": ["S7"]}],
    "private_banking":        {"present": "Yes", "detail": "...", "source_ids": []},
    "asset_management":       {"present": "Yes", "detail": "entity, AUM if any, fund range", "source_ids": []},
    "brokerage":              {"present": "Yes", "detail": "entity, markets covered, channel", "source_ids": []},
    "digital_investing":      {"present": "Yes", "detail": "app/platform name, what can be bought in-app, launch date", "source_ids": []},
    "advisory":               {"present": "Yes", "detail": "...", "source_ids": []},
    "discretionary":          {"present": "Unclear", "detail": "...", "source_ids": []},
    "model_portfolios_robo":  {"present": "No", "detail": "...", "source_ids": []},
    "funds_platform":         {"present": "Yes", "detail": "third-party funds shelf, platform provider if named", "source_ids": []},
    "structured_products":    {"present": "Yes", "detail": "...", "source_ids": []},
    "private_markets":        {"present": "Not found after research", "detail": "...", "source_ids": []},
    "islamic_wealth":         {"present": "Yes", "detail": "Shariah-compliant funds/portfolios/sukuk", "source_ids": []},
    "asset_classes": ["Local equities", "GCC equities", "US/international equities", "ETFs", "Mutual funds", "Bonds", "Sukuk", "Structured products", "Private markets / alternatives", "Gold / precious metals", "Crypto / digital assets", "Real estate funds"],
    "partners": [{"partner": "Saxo Bank", "kind": "Execution / platform technology", "what": "powers in-app trading", "date": "2026-07-30", "status": "Live", "source_ids": []}],
    "initiatives": [{"date": "2026-05-11", "what": "specific launch / acquisition / partnership / strategy statement", "source_ids": []}],
    "evidence_for_arta": {
      "opportunities": ["specific, evidenced statements, e.g. 'States goal to grow wealth AUM; app offers only local equities (S5)'"],
      "barriers": ["e.g. 'Runs in-house platform built with X (S9)'; 'Islamic-only: needs Shariah-screened products'"],
      "incumbent_vendors": ["named wealth/investment tech or product vendors with source"]
    }
  },
  "sources": [
    {"id": "S1", "title": "Executive Management", "publisher": "Emirates NBD", "url": "https://...",
     "doc_type": "Official leadership page", "tier": 2, "published": null, "accessed": "2026-10-12", "language": "en"}
  ],
  "original_reconciliation": [
    {"field": "Chief executive", "original_value": "...", "finding": "Confirmed | Corrected | Updated | Could not verify | Removed",
     "new_value": "...", "source_ids": ["S1"], "materiality": "Material | Minor"}
  ],
  "discrepancies": [{"field": "...", "detail": "what conflicts", "source_ids": ["S1", "S6"], "resolution": "what we used and why / unresolved"}],
  "open_items": ["what could not be verified, blocked pages, what to check next"],
  "research_status": "Complete | Partial",
  "researched_by": "agent batch id",
  "checked": "2026-10-12"
}
```
Notes:
- `tier` is an integer 1-5. Dates are ISO (YYYY-MM-DD, or YYYY-MM / YYYY when only that is known).
- `capabilities.asset_classes` lists only classes evidenced for this institution (not the whole example list).
- `original_reconciliation` is required only for institutions present in the original workbook (an extract is
  provided under research/original_extracts/<id>.json). Check EVERY original field and person listed there.
  Original LinkedIn URLs marked verified may be kept only if you have no contrary evidence; say so.
- For subsidiaries profiled separately (e.g. a bank-owned capital arm), set `parent_id` and explain double
  counting in `group_structure`.
- Target depth per institution: 8–15 people (CEO, chair, plus every relevant head from §2), all standard
  metrics available, every capability field assessed, 10–30 sources. Smaller firms will have fewer.

## 7. Before finishing
1. Validate each file: `python3 -c "import json,sys; json.load(open(sys.argv[1]))" <file>`.
2. Check every `source_ids` reference exists in `sources`.
3. Write a 5–10 line batch note to `research/batches/<batch_id>.md`: institutions done, notable corrections,
   unresolved items, blocked sources.
4. Final reply to the orchestrator: ≤120 words (files written + top 3 issues). The data lives in the files.
