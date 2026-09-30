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

Full proposal: see `docs/proposal/kaziforce-proposal.docx`.

## Project structure

```
kaziforce/
├── apps/
│   ├── web/                      # Next.js/React/TypeScript interface (not yet scaffolded)
│   └── api/                      # Flask REST API + hybrid recommendation engine
│       └── src/kaziforce_api/
│           ├── app.py            # Flask entry point
│           ├── matching/         # rule-based, semantic, and hybrid scoring
│           ├── explainability/   # graph traversal path extraction, explanation generation
│           └── data/             # loaders, preprocessing, database connection
├── packages/
│   └── knowledge-graph/          # ESCO backbone + Kenya vocabulary extension (import: kaziforce_kg)
│       └── src/kaziforce_kg/
├── data/                         # not committed — see data/README.md
├── tests/
├── docs/                         # proposal, diagrams, architecture notes
├── notebooks/                    # exploratory work
├── scripts/                      # one-off utilities (e.g. ESCO download)
└── .github/                      # CI workflow + issue templates
```

## Environment setup

Requires Python 3.12.

```bash
python -m venv venv
```

Activate it:
```bash
# macOS/Linux
. venv/bin/activate
# Windows (PowerShell)
venv\Scripts\Activate.ps1
```

**Install torch (CPU-only) first** — this avoids pulling several GB of unused
NVIDIA/CUDA packages that `sentence-transformers` would otherwise install by default:
```bash
pip install torch --index-url https://download.pytorch.org/whl/cpu
```

Then install everything else (this also installs `apps/api` and
`packages/knowledge-graph` in editable mode):
```bash
pip install -r requirements.txt
```

Copy the environment template and fill in real values:
```bash
cp .env.example .env
```

## Database setup

`DATABASE_URL` in `.env` works with either option:

**Option A — Supabase (recommended to start)**
1. Create a free project at [supabase.com](https://supabase.com).
2. In the SQL editor, run: `create extension if not exists vector;` (enables pgvector).
3. Go to Project Settings → Database → Connection string (URI), copy it into
   `DATABASE_URL` in your `.env`.

**Option B — Local PostgreSQL via CLI**
```bash
createdb kaziforce
psql kaziforce -c "CREATE EXTENSION IF NOT EXISTS vector;"
```
Then set `DATABASE_URL=postgresql://<user>:<pass>@localhost:5432/kaziforce` in `.env`.

Test the connection:
```bash
python -m kaziforce_api.data.db
```

## Running things

```bash
# API
flask --app kaziforce_api.app run

# Tests
pytest -v

# Lint
ruff check apps/api packages tests
```

## Development workflow

- `main` — stable
- `dev` — active work
- `feature/<name>` — branched from `dev`, merged via pull request

Sprint plan and progress tracking: see the GitHub Projects board and Milestones
(mirrors the six two-week sprints in the proposal's Chapter 3 methodology).

Commit convention: `feat:`, `fix:`, `docs:`, `chore:`, `test:` prefixes.

## Tech stack

Python · NetworkX · Sentence Transformers (all-MiniLM-L6-v2) · scikit-learn ·
Flask · Next.js/React/TypeScript · PostgreSQL + pgvector

## License

Academic project — Strathmore University, 2026.
