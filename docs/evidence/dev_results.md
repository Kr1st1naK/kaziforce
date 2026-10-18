# Development-split baseline results

Source: [`results/dev/20261017-132422_6698b8a/`](../../results/dev/20261017-132422_6698b8a/), produced by `scripts/evaluate.py` from commit `6698b8a`
(no uncommitted changes; 2026-10-17). 216 development workers each rank all 280
postings (80 synthetic, 200 Job Skill Set distractors); 8 postings are relevant
to each worker. Single deterministic run (tie-break seed 42); no confidence intervals.
Scoring rules: `docs/scoring-policy.md`, fixed before this run.

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
| *random among the 80 synthetic postings only (expected)* | 0.100 | 0.100 | 0.100 | 0.260 |

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

## Knowledge-graph effect

MRR with the knowledge graph minus MRR without it, for the same scorer (only the enricher differs).

| Scorer | Without KG → with KG | formal | known_alias | held_out | minimal | all |
|---|---|---|---|---|---|---|
| rule | rule_only → rule_kg | +0.215 | +0.665 | +0.000 | +0.723 | +0.475 |
| semantic | semantic_only → semantic_kg | +0.000 | +0.765 | +0.000 | +0.683 | +0.429 |
| hybrid | hybrid_no_kg → full | +0.016 | +0.683 | +0.000 | +0.720 | +0.420 |

## Response time per query (NFR-01)

Startup, once per run: 20.9 s (graph, job enrichment, model load and job embeddings). Per query: enrich the worker, score all postings, rank.

| Configuration | median ms | p95 ms | max ms |
|---|---|---|---|
| keyword | 3 | 9 | 174 |
| rule_only | 5 | 9 | 18 |
| rule_kg | 6 | 9 | 17 |
| semantic_only | 17 | 29 | 41 |
| semantic_kg | 35 | 51 | 63 |
| hybrid_no_kg | 6 | 8 | 9 |
| full | 7 | 9 | 13 |

## Reading these numbers: caveats

1. **Two reference levels.** A random ranking of all 280 postings gives MRR 0.106 and P@k 0.029. A ranking that
   only separates the 80 synthetic postings from the 200 distractors, and is random among the synthetic ones,
   gives MRR 0.260 and P@k 0.100. Distractors are US white-collar postings, so place names, KES amounts and
   trade vocabulary separate them easily. A score near the second level shows a configuration found Kenyan
   informal-trade postings, not the right trade.
2. **held_out is at the second level for every configuration** (MRR 0.22–0.36, P@5 0.10–0.16), and the
   knowledge graph adds exactly +0.000 there. This is by design: the withheld aliases have no path into the
   graph (`tests/test_kg_withheld.py`), and all-MiniLM-L6-v2 is an English model with no knowledge of
   *fundi wa stima* or *mshonaji*. rule_only and rule_kg are identical on held_out (MRR 0.312) because
   enrichment adds nothing to those profiles.
3. **The large gains on known_alias and minimal are expected by construction.** The synthetic postings list
   essential ESCO skills of their occupation, relevance is "same occupational area", and an included alias maps
   to that occupation's ESCO skills. Once enrichment maps the alias, skill overlap identifies the area almost
   exactly (rule_kg MRR 1.000 on both). The result shows that the mapping works end to end on unseen
   profiles that use known terms; it is not evidence about real Kenyan job postings.
4. **formal is near the ceiling without the graph** for keyword and semantic (MRR 1.000 and 0.992),
   because formal biographies repeat the ESCO occupation title and skill labels that the postings use.
5. **The labels ignore location, budget and availability**, so those rule criteria cannot raise these
   metrics. They can only reorder postings within an area, or demote a relevant one. This is why
   hybrid_no_kg is below its semantic component on formal profiles (P@5 0.791 vs 0.900).
6. **Hybrid vs rule with the graph.** On MRR, full (0.918) is not above rule_kg (0.924); on P@5 and P@10,
   full is higher (0.880 vs 0.832, 0.707 vs 0.692). With one seeded run and no confidence intervals, these
   differences are not tested for significance.
7. **P@10 cannot exceed 0.8** (8 relevant postings per worker).
8. **Area imbalance.** Electrician and Tailor have 30 base profiles each (12 others), and they supply all 24
   held_out queries, so the "all" column weights those two trades more heavily.
9. **Response time** is measured per query after startup (the model and job embeddings load once), on an
   8 GB Intel Core i5-8279U MacBook, CPU only. Every configuration's p95 is under 0.1 s and its maximum
   under 0.2 s, against the 5-second NFR-01 target. Startup is reported separately: 20.9 s.
