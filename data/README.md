# Data Directory

Raw and processed data are **not committed to git** (see `.gitignore`) — this
directory documents structure and provenance instead.

| Folder | Source | Status | How to (re)create |
|---|---|---|---|
| `raw/webmasters/` | Industry partner (Webmasters Kenya) | Not provided — partner supplied requirements documentation only (proposal §3.2.1) | — |
| `raw/job_skill_set/` | Job Skill Set (Mutlu, 2024), CC BY-SA 4.0 — supplementary job-side corpus | Present (1,167 postings; formal white-collar categories only — see its README) | Manual Kaggle download, see `raw/job_skill_set/README.md` |
| `raw/esco/` | ESCO public API — informal-trade subset (24 ISCO-08 unit groups) | Downloaded 2026-09-30: 128 occupations, 1,821 skills, 4,746 occupation–skill relations | `python scripts/download_esco.py` |
| `raw/kaikki/` | kaikki.org Swahili extract of Wiktionary (CC BY-SA 4.0 / GFDL) — dictionary checks for vocabulary aliases | Downloaded 2026-10-05 (file dated 2026-10-03), 21,306 entries | Download the Swahili file, see `raw/kaikki/README.md` |
| `raw/sw_wiktionary/` | Swahili Wiktionary pages (CC BY-SA 4.0): second dictionary source for vocabulary aliases | Fetched 2026-10-06: 85 titles, 46 Swahili entries | `python scripts/fetch_sw_wiktionary.py`, see `raw/sw_wiktionary/README.md` |
| `raw/synthetic/` | Generated programmatically, grounded in KNBS (KNOCS/ISCO-08) + ESCO | First version: 12 workers, 12 jobs across 8 occupations | `load_synthetic_data(regenerate=True)` |
| `processed/` | Cleaned, ESCO-mapped, vocabulary-mapped output of `apps/api/src/kaziforce_api/data/loaders.py` | — | `preprocess_jobs(load_job_corpus())` |
| `vocabulary/` | Kenya-specific informal trade term mappings (committed: `aliases.csv`, `area_esco_map.csv`, `dictionary_evidence.csv`) | 46 alias rows, all pending author review or rejected; none accepted yet. 10 areas shortlisted | `python scripts/map_vocabulary_areas.py`; `python scripts/fetch_sw_wiktionary.py`; `python scripts/check_vocabulary_dictionary.py` |

`raw/esco/download_manifest.json` records the exact download date, ISCO groups,
row counts, and any skill URIs the API failed to return.

See proposal Section 3.2.1 (Data Acquisition) for the full three-tier strategy.
