# Swahili Wiktionary pages (vocabulary dictionary checks)

| | |
|---|---|
| Source | Swahili Wiktionary, https://sw.wiktionary.org (MediaWiki API `action=query&prop=revisions`) |
| License | CC BY-SA 4.0 (attribution required) |
| File | `pages.json`: raw wikitext for 85 requested titles (50 pages exist, 46 with a Swahili section); not committed |
| Fetched | 2026-10-06 (`fetched_at` inside the file); 2 batched requests, 1.1 s apart, descriptive User-Agent |

**How to obtain:** `python scripts/fetch_sw_wiktionary.py` (titles come from
`data/vocabulary/aliases.csv`). Pages change over time, so a re-fetch may give
different results; keep the `fetched_at` date with any reported numbers.

Parsed offline by `scripts/check_vocabulary_dictionary.py` (part of speech and
English translations from the Swahili section only). No page text is written to
`data/vocabulary/`.
