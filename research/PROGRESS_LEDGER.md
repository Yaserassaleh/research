# Progress ledger — ARTA GCC FI Intelligence

Resume rule: the files in `research/institutions/` are the source of truth. A batch is done when every id in
`research/universe.json` → batches has a JSON file there and `python3 tools/build_db.py` reports no invalid JSON or
broken source references for it. Re-run any missing batch with the same prompt pattern (protocol + ids + leads).

## Setup (12 Oct 2026)
- [x] Original workbook preserved unchanged (SHA-256 037f596d…811e) in `00 Original workbook (unchanged)/`.
- [x] Audit of the original: 141 `#REF!` formulas (FX sheet deleted; USD columns all fail), 153 cited source IDs with no
      source-register sheet, 9 institutions missing from the Banks sheet, 14+14 inconsistent status phrasings,
      7 stale "original USD estimate" rows, internal ARTA figures stored as Wio metrics. See Correction log.
- [x] Per-institution extracts of the original: `research/original_extracts/` (23 institutions; Dhabi folded into Finance House).
- [x] Universe, inclusion criteria and batch plan: `research/universe.json` (106 institutions, 36 batches).
- [x] Protocol and schema: `research/RESEARCH_PROTOCOL.md`.
- [x] FX basis: `research/fx.json` (pegs; CBK KWD rates at 31 Dec 2025, 31 Mar, 30 Jun, 30 Sep 2026; FY2025 and H1 2026 averages).
- [x] Build tools: `tools/build_db.py`, `tools/build_workbook.py`, `tools/build_site.py`, `tools/site_template.html`.

## Batches
| Batch | Institutions | Status |
|---|---|---|
| P1 | ae-enbd, ae-ei | done 14:01 (reviewed) |
| P2 | sa-alinma, sa-alinma-capital | done 13:58 (reviewed) |
| P3 | ae-sarwa, kw-markaz | done 13:55 (Markaz partial: site bot-check) |
| B01 | ae-fab, ae-adcb | done (ADCB partial: sites 403, reports >10 MB) |
| B02 | ae-dib, ae-adib | files complete; agent stopped by account usage limit at 14:22 before batch note |
| B03 | ae-mashreq | done; ae-cbd → relaunched as R1 |
| B04 | ae-rakbank, ae-nbf | done; ae-sib → R1 |
| B05 | ae-bos, ae-ajman (complete), ae-cbi, ae-investbank (partial) | stopped by usage limit |
| B06 | ae-uab (complete), ae-nbq, ae-almasraf, ae-eib (partial: search quota) | done |
| B07 | ae-wio (complete), ae-zand (partial) | ae-ruya, ae-mbank → R2 |
| B08 | ae-financehouse, ae-alramz, ae-shuaa (complete), ae-intlsecurities (partial) | ae-arqaam → R2 |
| B09 | ae-baraka, ae-stashaway, kw-kic, om-ubhar | done |
| B10 | sa-snb (partial) | sa-snb-capital → R3 |
| B11 | sa-alrajhi | sa-alrajhi-capital → R3 |
| B12 | sa-riyad | sa-riyad-capital → R3 |
| B13 | sa-sab, sa-sab-invest | sa-bsf, sa-bsf-capital → R4 |
| B14 | sa-anb | sa-anb-capital, sa-albilad, sa-albilad-capital → R5 |
| R1–R5 | relaunched pieces of B02–B14 | done (CBD complete; SIB, Ruya, Mbank, Arqaam, BSF Capital, Albilad Capital partial) |
| B19, B20, B21, B23, B24, B25, B30, B33 | QNB, QIB, CBQ, Doha, MAR, Dukhan, Ahlibank, QIIB, Lesha, NBK, Boubyan, KFH, KFH Bahrain, Burgan, Kamco, Warba, Bank Muscat, Sohar, SCB, HSBC, Citi | done |
| B15, B26, B27, B29a | AlJazira (+capital), SAIB (+capital), Gulf Bank, CBK (partial), ABK, KIB, NBB, BisB, BBK, Bank ABC, GIB | done |
| B31, B16, B28, B17, B18, B22 | Bank Dhofar, NBO, OAB; STC/D360/Vision; Al Salam, Khaleeji; Derayah, Sahm; Jadwa; QInvest | files written before the session stopped |
| B17, B18, B22, B28, B29b, B32 | sa-abyan; sa-alkhabeer, sa-sedco; qa-dlala, bh-investcorp; bh-albaraka; bh-gfh, bh-sico; om-ahlibank, om-banknizwa | NOT STARTED (10 institutions) — needs a session with web access |
| Next | the 10 above; gap-closing on 22 partial profiles; check_links + verify_numbers; key-people spot check; republish | pending |

## Cloud session (12 Oct 2026, from 15:20)
The project moved to a Claude Code cloud session (repo Yaserassaleh/research). The GitHub web upload stopped at 100
files and flattened the folders, so tools/, research/original_extracts/, 00 Original workbook and 46 institution
files did not arrive.
- [x] Folder layout restored (research/, research/institutions/, research/batches/, exports/, site/).
- [x] 46 institution files restored from exports/database.json (18:40) with tools/restore_from_db.py; losses logged
      in research/central_edits.json (source notes; disclosure checks for metrics that have a value).
- [x] tools/status.py, build_db.py, build_site.py, build_workbook.py rebuilt and checked against the 18:40 outputs:
      database, CSVs, SQLite and QA report identical for the 75 institutions then built; the website byte-identical.
      Deliberate changes: percentages no longer converted to USD (4 metrics showed USD 0.0bn); ARTA score rounds half
      up like the workbook and website (7 totals +0.1); international banks' global group figures are kept out of
      headline KPIs (Citi, Standard Chartered).
- [x] Data the build needs that lived elsewhere: research/relationships.json (ARTA relationship status),
      research/original_workbook_ids.json (23 ids), research/original_value_match_1840.json (QA carry-over).
- [x] Full build: 96 institutions, 1,192 people, 1,318 metrics, 2,223 sources; 0 invalid JSON, broken source refs or
      vocabulary errors. 6 new QA flags accepted with reasons (research/qa_accepted.json).
- [x] tools/check_links.py, verify_numbers.py and pdftext.py rebuilt (same output formats; tested on a local server).
- [ ] Not possible here: the environment's network policy blocks outbound web access (WebFetch/curl fail; WebSearch
      works), so no research agents, link checks or number checks were run.
- [ ] original_value_match cannot be recomputed without research/original_extracts/ (18:40 results carried forward).

## Incidents
- 14:22: account usage limit hit with ~16 concurrent agents; all running agents stopped. Resumed 17:15 with ≤6 concurrent.
- WebSearch is rationed per agent; DuckDuckGo/Bing fallbacks serve challenge pages (not used). PDF tool added for >10 MB reports.

## Website
- Interim version published 12 Oct 2026: https://claude.ai/artifact/8Ae5QsZDFF5a2MLBdK6pDC (republish site/gcc-fi-intelligence.html to update the same URL).
- Cloud session, 12 Oct 2026: 96 institutions published at https://claude.ai/artifact/1eKXkN8WvRUvXGnTEhbMaH (a different Claude
  account from the interim link, which this account cannot open).

## Central QA
- research/qa_accepted.json — flags reviewed and accepted, with reasons.
- research/central_edits.json — every edit made centrally to agent files, with reason.
