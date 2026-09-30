# Data Directory

Raw and processed data are **not committed to git** (see `.gitignore`) — this
directory documents structure and provenance instead.

| Folder | Source | Status |
|---|---|---|
| `raw/webmasters/` | Industry partner (Webmasters Kenya), via industry attachment | Awaiting data |
| `raw/jobSkillData/` | Job Skill Set (Mutlu, 2024) — supplementary job-side corpus | Present |
| `raw/esco/` | ESCO taxonomy backbone (occupations, skills, hierarchies, alt labels) | Awaiting download |
| `raw/synthetic/` | Generated programmatically, grounded in KNBS + ESCO | Not yet generated |
| `processed/` | Cleaned, ESCO-mapped, vocabulary-mapped output of `apps/api/src/kaziforce_api/data/loaders.py` | — |
| `vocabulary/` | Kenya-specific informal trade term mappings | — |

See proposal Section 3.2.1 (Data Acquisition) for the full three-tier strategy.
