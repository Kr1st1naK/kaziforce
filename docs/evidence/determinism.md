# Is the scoring path deterministic?

Asked before the test-split run, so that Chapter 5 states what is actually true rather
than implying a robustness check that was never needed.

**Answer: yes.** Nothing in the scoring path is trained, sampled or randomised at
inference. Two complete runs on the same commit produce identical values in every
reported column, and the composite scores are identical bit for bit.

## The evidence

### Two full runs on one commit

Both runs are the development split, all seven configurations, 216 queries each, on
commit `46116e0` with a clean working tree.

| | Run |
|---|---|
| A | `results/dev/20261026-231918_46116e0` |
| B | `results/dev/20261026-232037_46116e0` |

```
=== raw file comparison ===
  metrics.csv     sha256 equal: False
  per_query.csv   sha256 equal: False

=== metrics.csv (35 rows) ===
  every non-timing column identical: True   rows differing: 0
  columns compared: configuration, variant, queries, P@3, P@5, P@10, MRR,
                    explained, coverage, coverage_inclusive, coverage_graph
  timing columns identical: False

=== per_query.csv (1512 rows) ===
  every column except query_ms identical: True   rows differing: 0
```

The file hashes differ **only** because each file carries wall-clock timings, which differ
between any two runs. Every reported number is identical.

### Composite scores, bit for bit

The run comparison above shows identical rankings and metrics, but `per_query.csv` records
ranks rather than scores, so it does not by itself prove the scores were identical. Checked
directly, with the model, the embedding cache and the recommender all built fresh each time:

```
workers compared .............. 20  (5600 scores)
identical ranking order ....... True
bitwise-identical composites .. True
max absolute difference ....... 0.000e+00
```

## Why it is deterministic, by inspection

| Possible source of variation | Why it does not apply |
|---|---|
| Model training | Nothing is trained. all-MiniLM-L6-v2 is used for inference only, at a pinned revision (`1110a243fdf4706b3f48f1d95db1a4f5529b4d41`). |
| Sampling at inference | There is none. Scoring is arithmetic over fixed vectors. |
| Dataset generation | The dataset is frozen and committed; the generator (seed 42) is not run as part of an evaluation, and `manifest.json` checksums are checked by the tests. |
| Tie-breaking | `pipeline.py` sorts the posting identifiers and then shuffles with `random.Random(42)`. Sorting first makes the order independent of insertion order, so the tie order is the same in every process. |
| Dictionary and set ordering | The embedding cache uses `dict.fromkeys`, which preserves insertion order, and the input order is the committed CSV order. No scoring decision is taken by iterating a set. |
| Weights | Fixed constants in `docs/scoring-policy.md`, never fitted to the data. |
| Explanation generation | Reads a finished match and writes nothing back. A test runs the evaluator twice over the same queries, with and without an explainer, and requires every ranking number to match. |

## What this means for Chapter 5

The honest statement is **determinism, not a missing robustness check**:

> The evaluation is a single run because the system is deterministic: nothing is trained
> and nothing is sampled at inference, so repeated runs on the same commit and the same
> frozen dataset produce identical metrics. Two such runs were compared and differed in no
> reported value. Confidence intervals over repeated runs would therefore all have zero
> width and would not be informative.

This should **not** be written as "a single seeded run without significance testing", which
implies variance exists and was not measured.

### What determinism does not claim

- **It is not a claim about variance across datasets.** One synthetic dataset was used.
  Whether these results hold on another dataset is untested, and remains a limitation.
- **It is not a claim about statistical significance between configurations.** The
  differences between configurations are differences between fixed numbers on one dataset,
  not estimates with sampling error. A paired test over per-query scores is possible
  (`per_query.csv` holds 216 paired observations per configuration) and would be the right
  tool if Chapter 5 wants to claim one configuration beats another; determinism does not
  remove that question, it only removes run-to-run noise.
- **It is not a claim about other machines.** Floating-point results could differ in their
  last bits on different hardware or a different BLAS. The claim is reproducibility of a
  run on the recorded machine, which `run.json` records.
