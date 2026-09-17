# Data Directory

Raw and processed data are **not committed to git** (see `.gitignore`) — this
directory documents structure and provenance instead.

| Folder | Source | Status |
|---|---|---|
| `raw/webmasters/` | Industry partner (Webmasters Kenya), via industry attachment | Awaiting data |
| `raw/jiji/` | Public listings, Jiji.co.ke "Services" / "Seeking Work" sections | Awaiting collection |
| `raw/synthetic/` | Generated programmatically, grounded in KNBS + ESCO | Not yet generated |
| `processed/` | Cleaned, ESCO-mapped, vocabulary-mapped output of `src/data/loaders.py` | — |
| `vocabulary/` | Kenya-specific informal trade term mappings (three-layer validated) | — |

See proposal Section 3.2.1 (Data Acquisition) for the full three-tier strategy.
