# Sprint II status

> **DRAFT for the author to edit (2026-10-18).** Sprint II as restructured by the supervisor: a working
> core workflow demonstrable from input through processing to output, with components integrated, plus
> initial evaluation evidence (a baseline pipeline, a justified validation approach and relevant
> metrics). Milestone: "Sprint II: Core workflow and baseline evaluation".

## 1. Summary

The core workflow runs end to end from the command line:

1. a worker profile goes in;
2. the knowledge graph enriches it;
3. rule-based and semantic scoring rank all 280 job postings;
4. the top K come out, each with its composite score, both components, the per-criterion breakdown
   and every matched skill with the graph path that produced it.

The same pipeline produced the development-split baseline: seven configurations, P@3/5/10 and MRR,
broken down by profile variant.

| Item | Status |
|---|---|
| Core workflow (input → processing → output) | **Done**: `scripts/run_recommendation.py`; transcript `docs/evidence/demo_run.txt` |
| Components integrated | **Done**: one `Recommender` used by the demo and the evaluation (§3) |
| Baseline evaluation | **Done**: run `results/dev/20261017-132422_6698b8a/`; summary `docs/evidence/dev_results.md` |
| Database as an integrated component | **In progress**: #41 (schema and migrations exist; the application reads CSVs until #41 is done) |
| REST endpoint `POST /recommend` | **In progress**: #38 |
| Release to `dev` and `main`, tag `sprint-II-done` | **Waiting for review**: PR #43 passes CI; branch protection on `dev` requires one approving review |

## 2. How to see it working

From a fresh clone (README "Setup from a fresh clone"):

    python scripts/run_recommendation.py --list 5
    python scripts/run_recommendation.py --worker-id 3917d39f-d0c0-46c2-aa34-9158711f68f3 --k 10
    python scripts/evaluate.py          # development split; writes a new run folder

The example worker writes *"Niko Nyeri, ni fundi wa umeme. Experience miaka 20, rates from KSh 2000."*
The knowledge graph maps *fundi wa umeme* to the ESCO occupation electrician and infers its 21
essential skills. All of the top 10 postings are electrical jobs, and each matched skill is shown as
"inferred via fundi wa umeme". The query takes about 70 ms after a startup of about 30 s (model
load and job embeddings).

## 3. Components and how they connect

| Component (Chapter 4 class) | Module | Role in the workflow |
|---|---|---|
| DataLoader | `kaziforce_api/data/data_loader.py` | Reads the frozen dataset as `WorkerProfile` / `JobPosting`; ground truth only on the evaluation side |
| VocabularyExtension | `kaziforce_kg/vocabulary.py` | The accepted informal terms; withheld aliases excluded |
| KnowledgeGraphBuilder, KnowledgeGraph | `kaziforce_kg/builder.py`, `graph.py` | Typed DiGraph, 544 nodes and 901 edges (`docs/evidence/kg_stats.md`) |
| Enricher (ProfileEnricher, NullEnricher) | `kaziforce_kg/enrichment.py` | Links a profile to the graph before scoring; worked example `docs/evidence/enrichment_example.md` |
| RuleBasedScorer, KeywordScorer, SemanticScorer, HybridScorer | `kaziforce_api/matching/` | Scoring as fixed in `docs/scoring-policy.md` before any score existed |
| Recommender | `kaziforce_api/pipeline.py` | Enrich, score and rank; the seven configurations are (enricher, scorer) pairs |
| Evaluator | `kaziforce_api/evaluation/` | Metrics, development-split guard, run folders |

## 4. Evaluation evidence

**Validation approach**
- **Split:** 156 base-profile groups split 40/20/40 into development, validation and test, by group,
  so all variants of a profile share a split. The split was written before any variant existed.
- **Labels:** a posting is relevant if it is in the worker's occupational area. The labels were
  frozen with the dataset and never derived from a scorer.
- **What this sprint used:** the development split only. A code guard rejects any other split, and
  the test split is reserved for the final evaluation.
- **Weights:** fixed a priori and not tuned against the labels, because the labels ignore location,
  budget and availability.

**Metrics.** P@3, P@5, P@10 and MRR over 216 development queries, each ranking 280 postings with
8 relevant. Response time per query is reported against NFR-01.

**Configurations.** Seven configurations: keyword (BM25), rule, rule + KG, semantic, semantic + KG,
hybrid without KG, and full. The three KG pairs differ only in the enricher, which locates where the
knowledge graph's effect comes from.

**Headline results (MRR):**

| Configuration | formal | known_alias | held_out | minimal | all |
|---|---|---|---|---|---|
| keyword (BM25) | 1.000 | 0.276 | 0.220 | 0.237 | 0.473 |
| hybrid without KG | 0.984 | 0.317 | 0.321 | 0.256 | 0.497 |
| full | 1.000 | 1.000 | 0.321 | 0.977 | 0.918 |

- **Where the KG helps:** it adds +0.665 to +0.765 MRR on known_alias and +0.683 to +0.723 on
  minimal, depending on the scorer, and +0.000 on held_out.
- **NFR-01:** p95 response time per query is under 0.1 s for every configuration, against the 5 s
  target.
- **How to read these numbers:** see `docs/evidence/dev_results.md` and `docs/limitations.md`.
  Gains on known terms are expected by construction, and held_out sits at the synthetic-only chance
  level.

## 5. Reproducibility and traceability

- **Fresh clone:** every input to the demo and the evaluation is committed: the dataset, the ESCO
  subset and the vocabulary. CI installs from a fresh clone and runs the 252 tests on every push and
  pull request.
- **Run folders:** each run folder records the commit, the data and knowledge-graph checksums, the
  scoring-policy checksum, the model revision, the weights, package versions and the machine.
  `evaluate.py` refuses to run on uncommitted changes.
- **Evidence files:** each file in `docs/evidence/` names the commit that generated it.
- **Test record:** `docs/test-results.xml`.

## 6. Changes from the original plan

| Planned | Done instead | Why |
|---|---|---|
| 70/15/15 split | 40/20/40 by group | Enough held-out queries per area at this dataset size |
| Graded relevance using location, budget and availability | Binary same-area relevance | Labels independent of every scorer; see limitations §5 |
| Weights tuned on validation data, with sensitivity analysis | Weights fixed a priori | Tuning against occupational labels would zero the location, budget and availability weights as an artefact |
| Embeddings in pgvector | In-memory cache | Unnecessary at 280 postings; pgvector moved to the Sprint III backlog (#45), after the UI |
| Keyword baseline as token overlap | Okapi BM25 | Comparable with the BM25 baselines in the literature; changed before any score existed |
| Five configurations | Seven | The rule + KG and semantic + KG pairs locate the KG's effect per component |
| `preprocess_jobs()` pipeline | Removed | Unused; distractors are cleaned once, at dataset build, by `clean_profile_text()` |

## 7. Issues found and corrected

- **Split leak in test controls (2026-10-16).** Two test controls read validation and test rows. No
  scores or relevance labels were computed on them. They were restricted to the development split,
  and the figures re-reported (64/64 and 24/24).
- **BMAD tooling still published.** It was untracked properly on 2026-10-17.
- **Process: PR #42 merged into `main` without going through `dev` (2026-10-17).** The release PR
  reconciles the two branches, and all work now goes through `dev` first.

## 8. Next (Sprint III)

1. #38: `POST /recommend`. Then the interface (four screens, `docs/wireframes/`).
2. #41: PostgreSQL as the application store (migrate, seed, CLI reads and writes `MatchScore`).
3. Explanation generator; final evaluation on the test split.
4. Backlog: #44 (flag listed skills that fit none of the reached occupations), #45 (pgvector, after the UI).
