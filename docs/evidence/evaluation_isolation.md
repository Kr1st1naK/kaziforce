# Evaluation isolation check

Re-ran the full development-split evaluation after the accounts and interface work, and
compared it with the run recorded before that work began.

| | Run | Commit | Date |
|---|---|---|---|
| Before | `results/dev/20261017-132422_6698b8a` | 6698b8a | 2026-10-17 |
| After | `results/dev/20261023-011125_75ba264` | 75ba264 | 2026-10-23 |

```
$ python scripts/evaluate.py          # after the interface work
metrics.csv      35 rows (7 configurations x 5 variant groupings)
  P@3, P@5, P@10, MRR identical ....... True   (0 rows differ)
  median_ms, p95_ms, max_ms identical . False   (wall-clock; differs between any two runs)
per_query.csv    1512 rows (7 configurations x 216 development queries)
  every column except query_ms identical  True   (0 rows differ)
```

**Every reported metric is identical.** Of 35 aggregate rows and 1,512 per-query rows,
none differs in P@3, P@5, P@10, MRR or the rank of the first relevant posting. The only
differences are the wall-clock timing columns, which differ between any two runs on any
machine and are not part of the reported results.

This holds because the evaluation never touches the API or the database: `scripts/evaluate.py`
builds its own pipeline from `DataLoader`, which reads the frozen CSV files
(requirement IR-07). The accounts work added only nullable columns and new endpoints.
