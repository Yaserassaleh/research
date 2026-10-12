# Executive deep-dive — addendum to RESEARCH_PROTOCOL.md (binding for the people pass)

Purpose: make every person record a verified, meeting-ready profile: exact current title, appointment date,
full career history, education, professional qualifications, LinkedIn (only where verifiable) and a re-checked
role status. Everything in RESEARCH_PROTOCOL.md §2 (verification, privacy, LinkedIn rules) and PILOT_LESSONS.md
still applies. This pass changes the `people` of the institutions in your batch, plus the `sources`,
`discrepancies` and `open_items` those changes need. Do not touch metrics, capabilities or other fields, and do not
touch other institutions' files.

Model entry (depth expected for a decision-maker): `research/institutions/kw-kfh.json`, person "David O'Loan".

## 1. Order of work for each institution (efficient: one document covers many people)
1. Open the official leadership pages (board, executive management, Shariah board, subsidiary boards/management)
   and the latest annual report's governance section ("Board of Directors", "Executive Management", "Corporate
   Governance Report"), which usually carry each person's education, career and appointment date. Read pages and
   PDFs with `python3 -E tools/pdftext.py "<url>"`; for large PDFs add
   `--grep "Executive Management|Board of Directors|qualification|holds a" --context 1500`.
   Arabic annual reports and Saudi Exchange / Boursa Kuwait / ADX / DFM / QSE / Bahrain Bourse / MSX
   board-appointment announcements are good sources too (they often state qualifications and experience).
2. For each person, compare the file with the official text and fill or correct every field (§2).
3. Then check 2025–2026 appointment and departure news for each decision-maker (§3).
4. Order inside the batch: decision-makers first (functions include CEO, Group CEO, Deputy CEO, Subsidiary CEO,
   Retail, Affluent, Private banking, Wealth, Investments / asset management, Brokerage, Digital, Technology,
   Innovation / partnerships, Strategy, or Chair) at full depth; then board, Shariah and other members: role
   confirmation from the official page or annual report, plus education, career and qualifications from the same
   documents. News checks for those only when the official listing has changed.
5. Add people only when needed: the named successor of someone who has left a decision-maker role, or a current
   head of wealth / private banking / asset management / brokerage / digital whose post appears on the official
   page but is missing from the file. Full depth for anyone you add.

## 2. Field standards
- `title`: exact current title as on the official source (English; keep the Arabic in `name_ar` only for names).
- `appointed`: date appointed to the CURRENT role (YYYY-MM-DD, YYYY-MM or YYYY as the source gives it).
  `appointed_note`: joining date if different, board-election dates, and which source gives which date.
- `previous_roles`: full career, newest first, with years wherever the source gives them, in the form
  `2016–2024 Deputy Group CEO Treasury & Investments, Ahli United Bank; 2015–2016 Group Treasurer, J Sainsbury plc; …`.
  End with `Current other roles: …` for board seats and outside posts. No adjectives, no summaries
  ("seasoned banker"), no years-of-experience claims unless that is all the source gives (then quote it).
- `education`: every degree as `Degree, Field, Institution` separated by `; ` (e.g. `MBA, University of
  Edinburgh; BSc Economics, American University of Beirut`). Add executive programmes only if the official bio lists
  them, after the degrees. Graduation years only if the official source prints them; never compute or state ages.
- `qualifications`: professional designations and licences (CFA, CPA, ACCA/FCCA, FRM, CAIA, CIA, Chartered Banker,
  CISI, regulator-approved person status) with the awarding body if given.
- `linkedin_url` / `linkedin_status`: follow protocol §2 exactly. Record a URL only if (a) an official site links
  it → "Verified (official link)", or (b) you opened the profile or a search result you saw shows the same name AND
  the same current employer AND a consistent title → "Verified (profile/search match)". Never guess or build a URL.
  The web-search tool in this environment declines name-based look-ups of individuals: do not try to get around
  that (no spelling tricks, no splitting names across queries). If a matching LinkedIn result appears in an
  ordinary search, it may be used under rule (b); otherwise leave `linkedin_url: null` and status "Not verified"
  (looked, not found) or "Not checked". Keep existing verified URLs unless you find contrary evidence.
- `role_status` and `role_evidence`: see §3. `role_evidence` names the official page and its check date, the news
  checked, and what each source says (e.g. "Executive Management page checked 2026-10-13 (S1); AR 2025 bio (S4);
  no 2025–2026 departure news found").
- `source_ids`: every source used for this person. `checked`: today's date.
- Professional information only: no contact details, ages, birth dates, family, nationality, religion, photos or
  personal social media. Do not infer reporting lines.

## 3. Current-role verification (every decision-maker; board members: official page + annual report suffice)
- "Verified current": the current official page (or a 2026 filing/announcement) lists the person in this role AND
  no later departure/appointment news contradicts it.
- "Departed": a dated official announcement or reputable report says they left the role. Keep the record, put the
  departure date and source in `role_evidence`, and add the successor if §1.5 applies.
- "Conflicting sources": the official page and news disagree; explain both in `role_evidence` and add a
  `discrepancies` entry.
- "Requires verification": only when the official page could not be read and no 2026 source confirms the role;
  say exactly what was blocked in `open_items`.
- News searches: search by institution and role ("<bank> appoints head of wealth management 2026",
  "<bank> chief executive resigns 2026"), in English and Arabic where useful (Argaam, Al Eqtisadiah, Al Khaleej).

## 4. Sources
- Add a `sources` entry for every new document (next free S-number), with tier: 1 annual report / filing /
  exchange announcement; 2 official site page or release; 3 regulator register; 4 official bio elsewhere or
  LinkedIn; 5 reputable news. `doc_type` says what it is ("Annual report — Board and Executive Management
  biographies", "Saudi Exchange announcement — board appointment", "LinkedIn profile (search result)").
- A source you did not open (seen only in search results, or blocked) carries `"note": "Seen in search results only"`.
- Aggregators and data brokers (theofficialboard, marketscreener, globaldata, crunchbase, zoominfo, rocketreach,
  Wikipedia) are leads only, never cited. If two reliable sources disagree on a fact (degree, year, title), keep
  the better-tier one, mention both in a `discrepancies` entry.

## 5. Finish
1. Validate each file: `python3 -c "import json,sys; json.load(open(sys.argv[1]))" <file>`; every `source_ids`
   reference must exist in `sources`; vocabularies per protocol §5.
2. Do not run tools/build_db.py or any build tool.
3. Write `research/people_pass/<BATCH>.md` (5–12 lines): people reviewed / added / marked departed, fields filled,
   LinkedIn found, blocked sources, notable corrections (e.g. "CEO left in Aug 2026; successor added").
4. Reply in ≤120 words.

## 6. Agent prompt template (batches in research/people_pass/plan.json; max 6 agents at once)

```
You are a senior GCC financial-institutions researcher doing an executive deep-dive for ARTA's partnerships
team. Today is <DATE>. Batch id: <BATCH>. Project folder: <ROOT> (do not run git or any build tool).

FIRST read in full: research/RESEARCH_PROTOCOL.md, research/PILOT_LESSONS.md and research/PEOPLE_DEEP_DIVE.md
(binding for this pass). Model entry: research/institutions/kw-kfh.json, person "David O'Loan".

Your institutions (edit only the people of these files, plus the sources, discrepancies and open_items those
edits need):
<- id — name (n people, k decision-makers)>

Decision-makers first at full depth, then board, Shariah and other members. READING WEB PAGES: the built-in
WebFetch tool cannot resolve hosts in this environment, so do not use it. Read every page and PDF with
`python3 -E tools/pdftext.py "<url>"` (run from the project folder; it prints the page text and lists any LinkedIn
links on the page; add `--grep "<regex>" --context 1500` for long documents or `--pages 1-15` for PDFs) or with
`curl -sSL "<url>"`. A site that answers 403/406 is bot-protected: record it in open_items and move on. Use
WebSearch for appointment/departure news by institution and role. The search tool declines name-based look-ups
of individuals: do not work around that. Never solve CAPTCHAs, bypass bot checks or log in. Open each
institution's leadership pages and annual-report governance section once and use them for everyone; budget about
6 tool calls per decision-maker and 2 per other person.

If pdftext.py and curl fail with network errors on every site you try, stop at once without editing any file and
reply "NO WEB ACCESS".

Write each institution file as soon as it is complete and validate it (JSON, source references, vocabularies).
Then write research/people_pass/<BATCH>.md and reply in ≤120 words.
```
