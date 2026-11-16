# Evaluation run 20261116-162048_7a12e4f

Split: **test** (216 worker queries, each ranking all 280 postings; 8 relevant per worker). Commit `7a12e4f`. Single deterministic run (seed 42); no confidence intervals.

## All variants

| Configuration | P@3 | P@5 | P@10 | MRR |
|---|---|---|---|---|
| keyword | 0.336 | 0.331 | 0.256 | 0.433 |
| rule_only | 0.211 | 0.201 | 0.163 | 0.431 |
| rule_kg | 0.850 | 0.820 | 0.679 | 0.915 |
| semantic_only | 0.353 | 0.336 | 0.272 | 0.460 |
| semantic_kg | 0.838 | 0.788 | 0.594 | 0.901 |
| hybrid_no_kg | 0.326 | 0.302 | 0.238 | 0.479 |
| full | 0.892 | 0.878 | 0.706 | 0.921 |
| *random ranking (expected)* | 0.029 | 0.029 | 0.029 | 0.106 |

## MRR by variant

| Configuration | formal | known_alias | held_out | minimal | all |
|---|---|---|---|---|---|
| keyword | 1.000 | 0.198 | 0.183 | 0.196 | 0.433 |
| rule_only | 0.749 | 0.328 | 0.341 | 0.249 | 0.431 |
| rule_kg | 0.984 | 0.984 | 0.341 | 0.992 | 0.915 |
| semantic_only | 1.000 | 0.229 | 0.319 | 0.203 | 0.460 |
| semantic_kg | 1.000 | 0.984 | 0.319 | 0.936 | 0.901 |
| hybrid_no_kg | 0.951 | 0.323 | 0.331 | 0.219 | 0.479 |
| full | 1.000 | 1.000 | 0.331 | 0.984 | 0.921 |

## P@5 by variant

| Configuration | formal | known_alias | held_out | minimal | all |
|---|---|---|---|---|---|
| keyword | 0.919 | 0.088 | 0.083 | 0.081 | 0.331 |
| rule_only | 0.413 | 0.128 | 0.133 | 0.088 | 0.201 |
| rule_kg | 0.875 | 0.875 | 0.133 | 0.969 | 0.820 |
| semantic_only | 0.912 | 0.094 | 0.142 | 0.075 | 0.336 |
| semantic_kg | 0.953 | 0.875 | 0.142 | 0.778 | 0.788 |
| hybrid_no_kg | 0.756 | 0.128 | 0.133 | 0.084 | 0.302 |
| full | 0.975 | 0.966 | 0.133 | 0.972 | 0.878 |

## Knowledge-graph effect (MRR, with KG minus without; same scorer, only the enricher differs)

| Scorer | Without KG → with KG | formal | known_alias | held_out | minimal | all |
|---|---|---|---|---|---|---|
| rule | rule_only → rule_kg | +0.236 | +0.656 | +0.000 | +0.743 | +0.484 |
| semantic | semantic_only → semantic_kg | +0.000 | +0.756 | +0.000 | +0.733 | +0.441 |
| hybrid | hybrid_no_kg → full | +0.049 | +0.677 | +0.000 | +0.765 | +0.442 |

## Explanation coverage (NFR-02)

Share of the top-10 results for which the generator can state at least one concrete, attributable reason. Definition fixed in `docs/scoring-policy.md` §7 before the generator was written. **Coverage** is the NFR-02 figure (a shared skill is required); the other two columns are reported for comparison. Computed over the whole top-10, never only the results above the display threshold.

| Configuration | Coverage (NFR-02) | Inclusive | Graph-traced |
|---|---|---|---|
| keyword | 0.000 | 0.000 | 0.000 |
| rule_only | 0.115 | 0.904 | 0.000 |
| rule_kg | 0.773 | 1.000 | 0.768 |
| semantic_only | 0.000 | 0.000 | 0.000 |
| semantic_kg | 0.000 | 0.000 | 0.000 |
| hybrid_no_kg | 0.150 | 0.904 | 0.000 |
| full | 0.787 | 1.000 | 0.782 |

NFR-02 is assessed against **full**, the deployed system: **78.7%** against a target of 85%. `keyword`, `semantic_only` and `semantic_kg` have no rule component, so they produce no matched skills and no assessed criteria; their coverage is 0 by construction, not by failure.

### Coverage by variant (NFR-02 rule)

| Configuration | formal | known_alias | held_out | minimal | all |
|---|---|---|---|---|---|
| keyword | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| rule_only | 0.388 | 0.000 | 0.000 | 0.000 | 0.115 |
| rule_kg | 0.864 | 0.861 | 0.000 | 0.884 | 0.773 |
| semantic_only | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| semantic_kg | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 |
| hybrid_no_kg | 0.505 | 0.000 | 0.000 | 0.000 | 0.150 |
| full | 0.881 | 0.883 | 0.000 | 0.891 | 0.787 |

## Response time per query (after startup)

Startup, once per run: 28.8 s (graph, job enrichment, model load and job embeddings). Per query: enrich the worker, score all postings, rank.

| Configuration | median ms | p95 ms | max ms |
|---|---|---|---|
| keyword | 3 | 9 | 163 |
| rule_only | 4 | 5 | 5 |
| rule_kg | 5 | 6 | 7 |
| semantic_only | 16 | 25 | 35 |
| semantic_kg | 32 | 47 | 143 |
| hybrid_no_kg | 6 | 7 | 9 |
| full | 7 | 8 | 9 |

Explanations are generated after the timer stops: they are evaluation output, not part of answering a query, so these timings stay comparable with runs recorded before coverage existed.

## Notes

- P@10 cannot exceed 0.8: each worker has 8 relevant postings.
- Ties are broken by one fixed random order of the postings (seed 42), the same for every configuration.
- Relevance is same occupational area; location, budget and availability do not affect it (docs/scoring-policy.md).
- Machine: macOS-15.8.1-x86_64-i386-64bit, Intel(R) Core(TM) i5-8279U CPU @ 2.40GHz, Python 3.12.2.
