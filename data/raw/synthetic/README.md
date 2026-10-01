# Synthetic data (fallback source)

Status: first working version — 12 worker profiles (`workers.csv`) and 12 job
postings (`jobs.csv`) across 8 occupations, generated with seed 42.

Grounded in KNBS occupational categories (KNOCS, which follows ISCO-08), ESCO
occupations and essential-skill labels, and candidate informal trade terms from
`data/vocabulary/README.md`. Worker biographies vary between formal English,
informal Swahili, and code-switched styles. No real personal identifiers (DR-07).

Used to simulate cold-start scenarios and supplement dataset volume (DR-05).

Regenerate: `load_synthetic_data(regenerate=True)` in
`apps/api/src/kaziforce_api/data/loaders.py`; generator specs live in
`apps/api/src/kaziforce_api/data/synthetic.py`.
