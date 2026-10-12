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
| B31 (+B32), B16, B28, B17, B18, B22 (+B29b) | Omani 5; STC/D360/Vision; Al Salam/Khaleeji/Al Baraka; Derayah/Sahm/Abyan; Jadwa/Alkhabeer/SEDCO; QInvest/Dlala/Investcorp/GFH/SICO | running (launched by ~20:00) |
| Next | gap-closing + key-people verification pass on partial profiles; final checks; build; republish | pending |

## Incidents
- 14:22: account usage limit hit with ~16 concurrent agents; all running agents stopped. Resumed 17:15 with ≤6 concurrent.
- WebSearch is rationed per agent; DuckDuckGo/Bing fallbacks serve challenge pages (not used). PDF tool added for >10 MB reports.

## Website
- Interim version published 12 Oct 2026: https://claude.ai/artifact/8Ae5QsZDFF5a2MLBdK6pDC (republish site/gcc-fi-intelligence.html to update the same URL).

## Central QA
- research/qa_accepted.json — flags reviewed and accepted, with reasons.
- research/central_edits.json — every edit made centrally to agent files, with reason.
