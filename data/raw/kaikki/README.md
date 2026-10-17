# kaikki.org Swahili dictionary (vocabulary dictionary checks)

| | |
|---|---|
| Citation | Ylonen, T. (2022). Wiktextract: Wiktionary as machine-readable structured data. *Proceedings of LREC 2022*, 1317–1325. |
| Source page | https://kaikki.org/dictionary/Swahili/ |
| License | Derived from Wiktionary: CC BY-SA 4.0 and GFDL (attribution required) |
| File | `kaikki.org-dictionary-Swahili.jsonl`: 81,475,806 bytes, 21,306 entries (not committed; see `data/README.md`) |
| Server date | Last-Modified 2026-10-03; downloaded 2026-10-05 |
| SHA-256 | `24fc43b28a31a88bd04dd6720b36c04d59d7d08bffa1a6ab6b2411cd7d465340` |

**How to obtain:** download the Swahili file only (not the multi-gigabyte
all-languages file) and place it in this folder:

    curl -A "<descriptive user agent>" -o kaikki.org-dictionary-Swahili.jsonl \
      https://kaikki.org/dictionary/Swahili/kaikki.org-dictionary-Swahili.jsonl

kaikki.org regenerates the file regularly, so a fresh download will not match
the checksum above; record the new date and checksum if you re-run the checks.

Used by `scripts/check_vocabulary_dictionary.py`. Only headwords, parts of
speech and category flags are written to `data/vocabulary/`; no glosses are
copied.
