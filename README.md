# KaziForce

An explainable knowledge graph-enhanced recommender for informal gig worker–job matching in Kenya.

Capstone project — BSc Informatics and Computer Science, Strathmore University.
Supervisor: Mr. Kevin Ochieng' Omondi.

## What this is

Kenya's informal gig economy is underserved by existing digital labour-matching
platforms, which depend on interaction history (failing new workers/jobs — the
cold-start problem), don't explain their recommendations, and don't capture
informal trade vocabulary (e.g. *fundi wa umeme* for electrician).

This project combines a domain-specific knowledge graph — built on the ESCO
taxonomy and extended with Kenya-specific informal trade vocabulary — with
rule-based and semantic similarity matching, to produce explainable worker–job
recommendations that work from the moment a worker or job joins the platform.

## Project structure

```
kaziforce/
├── apps/
│   ├── web/                      # Next.js/React/TypeScript interface (eight screens)
│   └── api/                      # Flask REST API + recommendation engine
│       └── src/kaziforce_api/
│           ├── app.py            # Flask entry point
│           ├── matching/         # rule-based, semantic, and hybrid scoring
│           ├── explainability/   # explanation generation
│           └── data/             # loaders, synthetic data generator, DB connection and migrations
├── packages/
│   └── knowledge-graph/          # ESCO backbone + Kenya vocabulary extension (import: kaziforce_kg)
│       └── src/kaziforce_kg/
├── data/                         # see data/README.md: vocabulary and synthetic dataset are committed;
│                                 # large or third-party raw data (ESCO, Job Skill Set, kaikki) is not
├── tests/
├── docs/                         # sprint plan, vocabulary report, wireframes, test record
├── notebooks/                    # exploratory work
├── scripts/                      # ESCO download, vocabulary pipeline, dataset build and reports
└── .github/                      # CI workflow + issue templates
```

**Current status.** The frozen vocabulary (`data/vocabulary/`) and the synthetic
evaluation dataset (`data/raw/synthetic/`) are built and tested. The knowledge
graph, enrichment, scorers, end-to-end pipeline, evaluation runner and
`POST /recommend` are built, with PostgreSQL as the application store. The web
interface covers the eight approved screens in `docs/UI views/`, behind a
phone-and-PIN sign-in that gives a worker's profile and a client's postings an
owner (a proof of concept, not a production auth system — `docs/limitations.md`
§7 says what it does and does not protect against). The explanation is composed
in the interface from the score components, provenance and graph paths the API
returns: plain words first, with the numbers behind a disclosure.

## Setup from a fresh clone

Requires Python 3.12 and git. No database, API key or downloaded data is needed
to run the tests or inspect the dataset: everything they use is committed.

```bash
git clone https://github.com/Kr1st1naK/kaziforce.git
cd kaziforce
python3.12 -m venv venv
. venv/bin/activate                 # Windows (PowerShell): venv\Scripts\Activate.ps1
```

**Install torch (CPU-only) first.** This avoids pulling several GB of unused
NVIDIA/CUDA packages that `sentence-transformers` would otherwise install:
```bash
pip install torch --index-url https://download.pytorch.org/whl/cpu
```

Then install everything else. This also installs `apps/api` and
`packages/knowledge-graph` in editable mode. Intel Macs get an older, compatible
torch/NumPy stack automatically through environment markers in `requirements.txt`.
```bash
pip install -r requirements.txt
```

Check the install:
```bash
pytest -v                                   # full suite; under a minute, no network needed
ruff check apps/api packages scripts tests  # lint
```

## Running things

```bash
# Synthetic dataset difficulty report (reads the committed dataset, rewrites
# data/raw/synthetic/difficulty_report.md)
python scripts/report_synthetic_difficulty.py

# End-to-end recommendation for one stored worker (reads PostgreSQL; add --source csv without a database)
python scripts/run_recommendation.py --list 5
python scripts/run_recommendation.py --worker-id <id> --k 10

# Development-split evaluation (writes results/dev/<time>_<commit>/)
python scripts/evaluate.py

# REST API (contract: docs/api.md)
flask --app kaziforce_api.app run          # engine ready after ~30 s; check http://127.0.0.1:5000/health

# Web interface (needs the API running; see apps/web/README.md)
cd apps/web && npm install
npm run dev -- --hostname 127.0.0.1        # http://127.0.0.1:3000
```

**Do not regenerate the synthetic dataset.** It is frozen: its input checksums are
in `data/raw/synthetic/manifest.json` and the tests fail if they drift. Rebuilding
without the (uncommitted) Job Skill Set CSV would silently drop the 200 distractor
postings and change every job ID and relevance pair. See
`data/raw/synthetic/README.md` before running `scripts/build_synthetic_dataset.py`.

Optional raw data (only needed to rebuild inputs, not to run anything above):
`python scripts/download_esco.py` for the ESCO subset, and the manual downloads
described in `data/raw/*/README.md`.

## Database

PostgreSQL is the application store: the command-line demo and the REST API read
worker profiles and job postings from it, and the demo writes each ranking to
`match_score`. The schema (proposal Figure 4.6, extended in migration 0002) is
defined as versioned SQL migrations in `apps/api/src/kaziforce_api/data/migrations/`.
The evaluation deliberately reads the frozen CSVs instead, so its results stay
traceable through the dataset checksums and run in CI without a database.
Without a database, use `--source csv` (demo) or `KAZIFORCE_PROFILE_SOURCE=csv` (API).

Copy the environment template and set `DATABASE_URL`:
```bash
cp .env.example .env
```

**Option A: Supabase.** Create a free project at [supabase.com](https://supabase.com),
then copy Project Settings → Database → Connection string (URI) into `DATABASE_URL`.

**Option B: local PostgreSQL** (13+). As a PostgreSQL superuser, create a
non-superuser app role that owns the database:
```bash
psql -d postgres -c "CREATE ROLE kaziforce_app LOGIN PASSWORD '<password>';"
createdb -O kaziforce_app kaziforce
psql kaziforce -c "REVOKE CREATE ON SCHEMA public FROM PUBLIC; GRANT USAGE, CREATE ON SCHEMA public TO kaziforce_app;"
```
Then set `DATABASE_URL=postgresql://kaziforce_app:<password>@localhost:5432/kaziforce` in `.env`.

Test the connection, create the schema, and load the dataset:
```bash
python -m kaziforce_api.data.db
python -m kaziforce_api.data.migrate          # safe to re-run; --status lists applied migrations
python scripts/seed_database.py              # development-split workers + all 280 postings; idempotent
python scripts/seed_database.py --reset      # clear profiles and postings stored through the API, then re-seed
```

With `DATABASE_URL` set, `pytest` also runs the PostgreSQL round-trip tests
(`tests/test_store.py`) in a throwaway schema; without it they are skipped.

## Development workflow

- `main`: stable, demo-able releases, tagged per sprint (e.g. `sprint-1-done`)
- `dev`: integration branch
- `sprint-N/<theme>`: sprint work, branched from `dev` and merged by pull request

CI (`.github/workflows/ci.yml`) runs ruff and pytest on pushes and pull requests
to `main` and `dev`. Progress is tracked in GitHub Milestones and Issues.

Commit convention: `feat:`, `fix:`, `docs:`, `chore:`, `test:`, `data:` prefixes.

## Tech stack

Python · NetworkX · Sentence Transformers (all-MiniLM-L6-v2) · Flask ·
PostgreSQL · Next.js / React / TypeScript

## Licensing

**Code and documentation:** © 2026 Kristina Kemoi. Submitted as academic work
for the BSc Informatics and Computer Science capstone at Strathmore University.
No open-source licence is granted; please ask before reusing.

**Third-party data** keeps its own licence:

| Data | Licence | Where |
|---|---|---|
| ESCO classification (occupations, skills) | © European Union; reused under the European Commission reuse policy (Decision 2011/833/EU), with attribution | `data/kg/` (graph inputs), skill labels in `data/raw/synthetic/`, ESCO URIs in `data/vocabulary/` |
| Job Skill Set (Mutlu, 2024) | CC BY-SA 4.0 | 200 cleaned postings in `data/raw/synthetic/jobs.csv` (`source=job_skill_set`); that adapted content stays CC BY-SA 4.0 |
| Wiktionary (kaikki.org extract, Swahili Wiktionary) | CC BY-SA 4.0 (and GFDL) | Glosses and entry URLs in `data/vocabulary/` |

Synthetic worker profiles are generated and contain no real personal data.
