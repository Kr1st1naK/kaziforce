# Evaluation run 20261026-231918_46116e0

Split: **development** (216 worker queries, each ranking all 280 postings; 8 relevant per worker). Commit `46116e0`. Single deterministic run (seed 42); no confidence intervals.

## All variants

| Configuration | P@3 | P@5 | P@10 | MRR |
|---|---|---|---|---|
| keyword | 0.353 | 0.347 | 0.257 | 0.473 |
| rule_only | 0.279 | 0.233 | 0.176 | 0.449 |
| rule_kg | 0.866 | 0.832 | 0.692 | 0.924 |
| semantic_only | 0.341 | 0.325 | 0.266 | 0.470 |
| semantic_kg | 0.819 | 0.780 | 0.598 | 0.899 |
| hybrid_no_kg | 0.329 | 0.309 | 0.252 | 0.497 |
| full | 0.878 | 0.880 | 0.707 | 0.918 |
| *random ranking (expected)* | 0.029 | 0.029 | 0.029 | 0.106 |

## MRR by variant

| Configuration | formal | known_alias | held_out | minimal | all |
|---|---|---|---|---|---|
| keyword | 1.000 | 0.276 | 0.220 | 0.237 | 0.473 |
| rule_only | 0.785 | 0.335 | 0.312 | 0.277 | 0.449 |
| rule_kg | 1.000 | 1.000 | 0.312 | 1.000 | 0.924 |
| semantic_only | 0.992 | 0.220 | 0.361 | 0.238 | 0.470 |
| semantic_kg | 0.992 | 0.984 | 0.361 | 0.921 | 0.899 |
| hybrid_no_kg | 0.984 | 0.317 | 0.321 | 0.256 | 0.497 |
| full | 1.000 | 1.000 | 0.321 | 0.977 | 0.918 |

## P@5 by variant

| Configuration | formal | known_alias | held_out | minimal | all |
|---|---|---|---|---|---|
| keyword | 0.938 | 0.097 | 0.100 | 0.100 | 0.347 |
| rule_only | 0.494 | 0.144 | 0.158 | 0.091 | 0.233 |
| rule_kg | 0.891 | 0.891 | 0.158 | 0.969 | 0.832 |
| semantic_only | 0.900 | 0.072 | 0.117 | 0.081 | 0.325 |
| semantic_kg | 0.950 | 0.912 | 0.117 | 0.725 | 0.780 |
| hybrid_no_kg | 0.791 | 0.113 | 0.133 | 0.091 | 0.309 |
| full | 0.975 | 0.978 | 0.133 | 0.966 | 0.880 |

## Knowledge-graph effect (MRR, with KG minus without; same scorer, only the enricher differs)

| Scorer | Without KG → with KG | formal | known_alias | held_out | minimal | all |
|---|---|---|---|---|---|---|
| rule | rule_only → rule_kg | +0.215 | +0.665 | +0.000 | +0.723 | +0.475 |
| semantic | semantic_only → semantic_kg | +0.000 | +0.765 | +0.000 | +0.683 | +0.429 |
| hybrid | hybrid_no_kg → full | +0.016 | +0.683 | +0.000 | +0.720 | +0.420 |

## Explanation coverage (NFR-02)

Share of the top-10 results for which the generator can state at least one concrete, attributable reason. Definition fixed in `docs/scoring-policy.md` §7 before the generator was written. **Coverage** is the NFR-02 figure (a shared skill is required); the other two columns are reported for comparison. Computed over the whole top-10, never only the results above the display threshold.

| Configuration | Coverage (NFR-02) | Inclusive | Graph-traced |
|---|---|---|---|
| keyword | 0.000 | 0.000 | 0.000 |
| rule_only | 0.125 | 0.890 | 0.000 |
| rule_kg | 0.782 | 0.998 | 0.775 |
| semantic_only | 0.000 | 0.000 | 0.000 |
| semantic_kg | 0.000 | 0.000 | 0.000 |
| hybrid_no_kg | 0.159 | 0.890 | 0.000 |
| full | 0.792 | 0.998 | 0.787 |

NFR-02 is assessed against **full**, the deployed system: **79.2%** against a target of 85%. `keyword`, `semantic_only` and `semantic_kg` have no rule component, so they produce no matched skills and no assessed criteria; their coverage is 0 by construction, not by failure.

### Coverage by variant (NFR-02 rule)

| Configuration | formal | known_alias | held_out | minimal | all |
|---|---|---|---|---|---|
| keyword | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| rule_only | 0.420 | 0.000 | 0.000 | 0.000 | 0.125 |
| rule_kg | 0.881 | 0.880 | 0.000 | 0.878 | 0.782 |
| semantic_only | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| semantic_kg | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| hybrid_no_kg | 0.536 | 0.000 | 0.000 | 0.000 | 0.159 |
| full | 0.892 | 0.903 | 0.000 | 0.878 | 0.792 |

## Response time per query (after startup)

Startup, once per run: 37.2 s (graph, job enrichment, model load and job embeddings). Per query: enrich the worker, score all postings, rank.

| Configuration | median ms | p95 ms | max ms |
|---|---|---|---|
| keyword | 6 | 17 | 459 |
| rule_only | 8 | 9 | 13 |
| rule_kg | 10 | 11 | 13 |
| semantic_only | 26 | 38 | 52 |
| semantic_kg | 55 | 80 | 316 |
| hybrid_no_kg | 12 | 15 | 19 |
| full | 14 | 17 | 20 |

Explanations are generated after the timer stops: they are evaluation output, not part of answering a query, so these timings stay comparable with runs recorded before coverage existed.

## Notes

- P@10 cannot exceed 0.8: each worker has 8 relevant postings.
- Ties are broken by one fixed random order of the postings (seed 42), the same for every configuration.
- Relevance is same occupational area; location, budget and availability do not affect it (docs/scoring-policy.md).
- Machine: macOS-15.8.1-x86_64-i386-64bit, Intel(R) Core(TM) i5-8279U CPU @ 2.40GHz, Python 3.12.2.
