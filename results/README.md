# Evaluation results

Each folder under `dev/` is one run of `scripts/evaluate.py` on the
**development split**, named `<YYYYMMDD-HHMMSS>_<commit>`. Run folders are
committed and never overwritten.

| File | Contents |
|---|---|
| `metrics.md` | Readable tables: all variants, MRR and P@5 by variant, knowledge-graph effect, response time |
| `metrics.csv` | The same aggregates, one row per configuration × variant |
| `per_query.csv` | One row per configuration × worker: first relevant rank, reciprocal rank, P@3/5/10, query time |
| `run.json` | Code and data versions: commit, uncommitted-changes flag, dataset and KG checksums, scoring-policy checksum, model revision, weights, packages, machine |

The validation and test splits are not evaluated here. Partial runs go to
`scratch/`, which is not committed. The interpretation and caveats of the
current run are in `docs/evidence/dev_results.md`.
