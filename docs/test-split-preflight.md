# Pre-flight checklist for the test-split evaluation

The test split is evaluated **once**. The run is committed immediately, before the numbers
are discussed, and is not repeated after seeing the results. This checklist is what must be
frozen and recorded first, and the audit showing the split has not already been used.

## 1. The test split has never been read by anything that scores

**Audited on 2026-10-26.** Three independent checks.

### The guard, in every commit that has ever existed

`apps/api/src/kaziforce_api/evaluation/evaluator.py` refuses any split but `development`:

```python
EVALUATION_SPLITS = ("development",)
...
if split not in EVALUATION_SPLITS:
    raise ValueError(f"split {split!r} may not be evaluated; ...")
```

Only two commits have ever touched that file (`6698b8a`, `46116e0`), and the constant reads
`("development",)` in both. It has never included `test`, so no evaluation has ever been
able to run on it. Allowing it is a deliberate, recorded code change, not a flag.

### Every run folder that exists

| Run | Split |
|---|---|
| `results/dev/20261017-132422_6698b8a` | development |
| `results/dev/20261023-011125_75ba264` | development |
| `results/dev/20261025-225302_1ae4e60` | development |
| `results/dev/20261026-231918_46116e0` | development |
| `results/dev/20261026-232037_46116e0` | development |
| `results/scratch/20261017-132231_7aef3e0` | development |

No run on any other split exists.

### Every call site that selects a split

Only three places name the test split, and none of them scores anything:

| Place | What it does |
|---|---|
| `tests/test_data_loader.py::test_split_counts` | Counts rows per split. A count, not content. |
| `tests/test_data_loader.py::test_worker_lookup_is_restricted_to_the_split` | Reads one test worker's **identifier only**, to assert the loader refuses to return it under `development`. This is the guard being tested. |
| `scripts/seed_database.py` | `--split` is declared `choices=["development"]`, so the test split cannot be loaded into the application database at all. |

No scorer, recommender, evaluator or report has ever read a test-split worker's biography,
skills, location, rate or availability.

## 2. Frozen before the run

Each item must be committed, with nothing uncommitted in the working tree. `scripts/evaluate.py`
refuses to run on a dirty tree unless `--allow-dirty` is passed, and the run must **not** use
that flag, so the results map to exactly one commit.

| What | Where | Frozen by |
|---|---|---|
| The dataset | `data/raw/synthetic/` | `manifest.json` input checksums, asserted by `tests/test_synthetic_dataset.py` |
| The splits | `data/raw/synthetic/splits.csv` | Committed; group-level, assigned before any scorer existed |
| The vocabulary | `data/vocabulary/aliases.csv` | Decisions committed in `dc033d8`, before the data was generated |
| The knowledge graph inputs | `data/kg/` | Checksums recorded in `run.json` |
| The scoring policy | `docs/scoring-policy.md` | Checksum recorded in `run.json`; weights are constants, never fitted |
| The model | all-MiniLM-L6-v2 | Pinned revision `1110a243fdf4706b3f48f1d95db1a4f5529b4d41` |
| The coverage definition | `docs/scoring-policy.md` §7 | Committed in `27a7254` and `10abe1b`, before the generator existed |
| The seed | 42 | Tie-break and dataset generation |

## 3. Recorded by the run itself

`run.json` is written automatically and records: the commit and whether the tree was dirty,
the split, the query count, the seed, every configuration's (enricher, scorer) pair, the
rule weights, the hybrid α and β, the BM25 parameters, the model name and revision, the
dataset and knowledge-graph checksums, the scoring-policy checksum, package versions, and
the machine. Nothing needs to be noted by hand.

## 4. Decisions that must be made before the run, not after

These are fixed here so that no choice can be made in light of a result.

- **The headline metrics** are P@3, P@5, P@10 and MRR, macro-averaged over queries, plus
  explanation coverage under the strict rule and median / p95 / max response time. Reported
  for all seven configurations, and broken down by the four variants.
- **NFR-02 is assessed against `full`** at a target of 85% (`docs/scoring-policy.md` §7).
- **NFR-01 is assessed against the per-query engine time**, with startup reported separately,
  and the known gap that this is not browser-to-browser time (traceability, NFR-01).
- **The result stands.** If a target is missed, it is reported as missed. No threshold,
  weight, definition or configuration is changed afterwards, and the run is not repeated.
  Any later change to the system is a *new* development-split result, not a revised test
  result.
- **One run is enough** because the system is deterministic; see `docs/evidence/determinism.md`.

## 5. Running it yourself

The test split is 216 workers, the same size as development, so the run costs about the
same: **roughly 35 s of startup and 35 s of queries, about a minute and a half in total**
for all seven configurations.

### Step 1 — check the tree is clean

```bash
git status --porcelain          # must print nothing
```

If anything is uncommitted, commit it first. `scripts/evaluate.py` refuses to run on a
dirty tree, and the run **must not** use `--allow-dirty`: that flag would record
"uncommitted_changes": true in `run.json` and the results would not map to one commit.

### Step 2 — make the enabling change, and commit it on its own

Two edits. Both are deliberately code, not a flag, so they appear in the history.

In `apps/api/src/kaziforce_api/evaluation/evaluator.py`:

```diff
-EVALUATION_SPLITS = ("development",)
+EVALUATION_SPLITS = ("development", "test")
```

In `scripts/evaluate.py`, add the argument and pass it through:

```diff
     parser.add_argument("--allow-dirty", action="store_true", ...)
+    parser.add_argument("--split", default="development", choices=["development", "test"])
...
-    evaluator = Evaluator(loader, recommenders, max_queries=args.max_queries,
+    evaluator = Evaluator(loader, recommenders, split=args.split, max_queries=args.max_queries,
                           explainer=ExplanationGenerator(kg))
```

The run folder is chosen by `scripts/evaluate.py` and currently goes to `results/dev/`.
Send a test run somewhere of its own:

```diff
-    base = REPO_ROOT / "results" / ("scratch" if args.max_queries else "dev")
+    base = REPO_ROOT / "results" / ("scratch" if args.max_queries else
+                                    "test" if args.split == "test" else "dev")
```

Then:

```bash
python -m pytest -q                     # 381 tests; the guard test now expects test to be allowed
git add -A && git commit -m "evaluation: allow the test split for the final run"
```

One existing test will fail and must be updated, not deleted:
`tests/test_evaluation.py::test_only_the_development_split_may_be_evaluated` is
parametrised over `validation`, `test`, `train`. Drop `test` from that list and leave the
other two, so the guard is still proved to work.

### Step 3 — run it, once

```bash
. venv/bin/activate
python scripts/evaluate.py --split test
```

Expect it to print the metrics table and `Written to results/test/<timestamp>_<commit>`.

### Step 4 — commit before reading

```bash
git add results/test && git commit -m "evaluation: test-split run <timestamp>_<commit>"
```

Confirm only that it completed and that `run.json` says `"split": "test"` and
`"uncommitted_changes": false`. **Then** read `metrics.md`.

### If something goes wrong mid-run

A crash is not a result. Fix the cause, commit the fix, and run again — that is a first
run, not a second. What must not happen is a *completed* run being discarded or repeated
because of what it showed.

## 6. After the run

1. The run folder is committed, unread beyond the two checks above.
2. Read `metrics.md`.
3. Record the figures in `docs/traceability.md` against NFR-01, NFR-02 and FR-08, and in
   Chapter 5.
4. If a target is missed, it is reported as missed. Any later change to the system
   produces a **new development-split result**, never a revised test result.
