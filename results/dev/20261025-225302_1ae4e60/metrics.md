# Evaluation run 20261025-225302_1ae4e60

Split: **development** (216 worker queries, each ranking all 280 postings; 8 relevant per worker). Commit `1ae4e60` **with uncommitted changes**. Single deterministic run (seed 42); no confidence intervals.

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

## Response time per query (after startup)

Startup, once per run: 23.7 s (graph, job enrichment, model load and job embeddings). Per query: enrich the worker, score all postings, rank.

| Configuration | median ms | p95 ms | max ms |
|---|---|---|---|
| keyword | 4 | 11 | 181 |
| rule_only | 6 | 8 | 12 |
| rule_kg | 7 | 8 | 10 |
| semantic_only | 17 | 27 | 35 |
| semantic_kg | 37 | 54 | 68 |
| hybrid_no_kg | 7 | 9 | 10 |
| full | 8 | 10 | 20 |

## Notes

- P@10 cannot exceed 0.8: each worker has 8 relevant postings.
- Ties are broken by one fixed random order of the postings (seed 42), the same for every configuration.
- Relevance is same occupational area; location, budget and availability do not affect it (docs/scoring-policy.md).
- Machine: macOS-15.8.1-x86_64-i386-64bit, Intel(R) Core(TM) i5-8279U CPU @ 2.40GHz, Python 3.12.2.
