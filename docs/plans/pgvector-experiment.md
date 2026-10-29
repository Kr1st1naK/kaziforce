# Plan: pgvector as a Chapter 5 comparison (issue #45)

**Status: plan only. Nothing here is built.** Written 2026-10-29, after the supervisor asked
for pgvector "for comparison", which makes it an experiment to report rather than a feature
to ship.

## What is being compared

Today the semantic component holds a 280 × 384 float32 matrix in memory (420 KiB) and scores
one worker against every posting with a single NumPy dot product: `vectors[1:] @ vectors[0]`
in `matching/semantic.py`. The pgvector path would store the same 384-dimensional embeddings
in a `vector(384)` column on `job_posting` and ask PostgreSQL for the nearest neighbours with
`ORDER BY embedding <=> %s LIMIT k`.

The comparison is therefore **retrieval mechanism only**. The embeddings, the model, the text
rule and the hybrid weighting are identical on both paths; only where the arithmetic happens
changes.

## 1. Proving the two paths rank identically

This is the part that matters most, because a comparison between a correct path and a subtly
different one would be worthless.

**The exactness condition.** pgvector returns *exact* results with no index, and *approximate*
results with an IVFFlat or HNSW index. The experiment therefore has three arms, not two:

| Arm | Mechanism | Expected to be identical to in-memory? |
|---|---|---|
| A | In-memory NumPy (today) | — the reference |
| B | pgvector, sequential scan, no index | Yes, up to float rounding |
| C | pgvector, HNSW or IVFFlat index | **No** — approximate by design |

Conflating B and C is the easy mistake. Arm C is allowed to differ, and measuring *how much*
it differs is itself a result.

**The operator must match the metric.** Embeddings are already L2-normalised
(`semantic.py: embed`), so cosine similarity equals the dot product. pgvector's `<=>` is
cosine *distance*, so similarity is `1 - (a <=> b)`. Getting this wrong gives a plausible but
wrong ranking, so the first test asserts the conversion on hand-computed vectors before any
posting is involved.

**How to prove it.**

1. **Round-trip the vectors.** Write the 280 embeddings to the column, read them back, and
   assert `np.array_equal` against the in-memory matrix. `vector` stores float32, which is
   what the matrix already holds, so this should be exact. If it is not, everything downstream
   is explained by storage, not by retrieval.
2. **Compare scores, not just order.** For all 216 development workers × 280 postings, compute
   the similarity both ways and assert `np.allclose(atol=1e-6)`. Report the maximum absolute
   difference rather than just a pass.
3. **Compare the rankings.** For arm B, assert the top-50 posting identifiers are *identical
   in order*, including the tie-break. This is where a difference would really show: ties are
   broken by `_tie_order` in the Python path, and `ORDER BY` in SQL would break them by
   whatever comes out of the scan unless the tie-break column is added explicitly. The SQL
   must order by `(distance, tie_order)` or the comparison fails for a reason that has nothing
   to do with pgvector.
4. **Run the evaluation on both.** Add the pgvector recommender as a configuration and run the
   development split. Arm B must reproduce `full`'s metrics exactly — 0 of 35 aggregate rows
   differing, the same check already used in `docs/evidence/evaluation_isolation.md`. That is
   the strongest statement available: not "the scores look close" but "every reported metric
   is identical".
5. **Quantify arm C's disagreement** rather than asserting it away: rank-biased overlap or
   simple top-k agreement against arm A, plus the change in P@5 and MRR. An index that costs
   0.00 MRR at 280 postings is a different finding from one that costs 0.05.

## 2. What to measure

**At the real scale (280 postings).** Retrieval time only — the embedding of the worker's text
is identical on both paths and would otherwise dominate and hide the comparison. Measure the
dot product in isolation on one side, and the SQL query round trip on the other, median and
p95 over the 216 development queries.

**At synthetic larger scales.** This is the only way the comparison becomes interesting, and it
is feasible: duplicate the 280 embeddings with small random perturbations to 10³, 10⁴, 10⁵ and
10⁶ rows. These are *not* real postings and must never touch the evaluation; they exist to plot
retrieval time against corpus size. Plot three curves (A, B, C) on log-scaled axes.

Worth stating explicitly in Chapter 5: the in-memory curve is expected to be linear in corpus
size and the HNSW curve roughly logarithmic, so they must cross somewhere. **Finding where they
cross is the actual experimental result**, and it is a more useful sentence than any number at
280.

**Also measure, because they are the real costs:** index build time, index size on disk, and
memory held by the Python process in arm A (420 KiB at 280 postings; 1.5 GiB at 10⁶).

## 3. What the comparison can honestly conclude at this scale

**It cannot conclude that pgvector is faster.** At 280 postings the in-memory dot product is a
single 280 × 384 matrix multiply on 420 KiB — microseconds, and already inside a query path
whose measured median is 14.8 ms end-to-end in the browser. Any SQL round trip adds network
and parsing overhead larger than the arithmetic it replaces. The expected result is that
**pgvector is slower at this scale, and that this is not a criticism of pgvector**.

**It also cannot conclude much about accuracy**, because arm B should be identical and arm C's
error at 280 rows is likely zero — an approximate index over 280 vectors has nothing to
approximate away.

**What it can honestly conclude:**

- Whether the pgvector path is *correct* — that is, reproduces the ranking exactly (arm B).
  A binary, defensible result.
- The **crossover point**: the corpus size beyond which pgvector wins. That is the honest
  answer to "should this system use pgvector", and it is a statement about *when*, not *whether*.
- The **cost of the current design's assumption**: embeddings are recomputed at every startup
  (about 35 s) because nothing is persisted. Persisting them removes that cost regardless of
  which path does the search, which is arguably the stronger argument for the column than
  retrieval speed is.

**The dishonest conclusions to avoid.** "pgvector is slower, therefore it is the wrong choice"
— true only at 280 postings, which is a property of this dataset, not of the design. And
"pgvector would scale the system to millions of workers" — untested, and the bottleneck at that
size would be the embedding of incoming text, not the search.

## 4. Scope and sequencing

Deliberately **after** the test-split evaluation, and on its own branch. It touches
`matching/semantic.py`, which the final results depend on; running it first would mean the
reported results came from a commit that had just been reorganised for an experiment.

Rough shape: a migration adding `job_posting.embedding vector(384)` (nullable, so the existing
seed is unaffected), a `PgVectorSemanticScorer` realising the existing `Scorer` interface so it
drops into `CONFIGURATIONS` without touching the scorers, a benchmark script writing to
`results/pgvector/`, and a `docs/evidence/pgvector_comparison.md`. The separability that
NFR-03 already requires is what makes this a drop-in rather than a rewrite.

**Not in scope:** making pgvector the default, storing worker embeddings, or any change to how
the deployed system retrieves. If the experiment shows a crossover far above 280, the honest
outcome is a documented comparison and no change to the application.
