# Pilot lessons — addendum to RESEARCH_PROTOCOL.md (binding)

The pilot file `research/institutions/ae-sarwa.json` is a good example of the depth and honesty expected
(regulator registers checked, conflicts logged, company claims labelled as such). Additional rules:

1. Metric keys: use the standard keys in protocol §4. Client assets that are not labelled AUM → `wealth_client_assets`.
   Trading volume → `brokerage_trading_value`. Do not invent other keys for standard concepts.
2. `period_type` is exactly "point_in_time" or "duration". `period_end` is YYYY-MM-DD; use YYYY-MM only when the
   source gives only a month.
3. Balance-sheet figures: take the exact number from the financial statements (thousands/millions as printed) when
   accessible; if only a rounded press-release figure is available, say "rounded" in `note`.
4. `model` for non-banks and bank-owned capital arms: "Not applicable" unless the whole firm is Shariah-compliant
   (then "Islamic"). Islamic product lines belong in `capabilities.islamic_wealth`.
5. A source seen only in search results (page not opened, e.g. 403) must carry `"note": "Seen in search results only"`.
   Prefer opening the page. LinkedIn profiles are normally search-result matches — say so.
6. Parent vs subsidiary: if a subsidiary has its own file (linked_id), put its metrics, people and capabilities in
   that file; in the parent, list it under `subsidiaries` with `linked_id` and keep parent metrics at group scope.
   If the subsidiary is NOT profiled separately, record its AUM/people in the parent with scope "Subsidiary: <name>".
7. Big banks: the people list must include (where they exist) Chair, Group CEO, Deputy CEO(s), heads of retail /
   personal banking, affluent/priority, private banking, wealth management, asset management, brokerage/securities,
   digital/technology/innovation, strategy, and CEOs of relevant wealth/investment subsidiaries. 10–18 people.
8. ARTA relevance evidence must be specific to the institution (named products, vendors, dates). No generic lines.
9. Customers: say whether the number is registered, active or total, and retail vs all.
10. Keep each JSON file under ~70 KB: don't repeat the same paragraph in several fields.
11. Leads given in the prompt come from internal notes and may be wrong. Verify from sources or leave them out; if a
    lead proves wrong, add an `open_items` line saying so (that is useful).
12. Search is rationed per agent (see protocol §2). Spend searches on: leadership changes in 2025–2026, the wealth
    and digital heads, LinkedIn matches for key people, and recent wealth/digital launches. Get financials and
    leadership lists by WebFetch from official pages and exchange filings.
13. Large or blocked PDFs: use tools/pdftext.py as described in protocol §2.
14. Do not run tools/build_db.py (it rewrites shared exports while other agents work). Validate your own JSON only.
