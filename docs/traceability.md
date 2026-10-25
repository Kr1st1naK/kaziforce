# Requirements traceability

Every requirement in Chapter 4, mapped to the code that implements it, the tests
that check it, and the evidence that demonstrates it. Unimplemented requirements
say so.

> **Needs your input.** The wording of each requirement below is taken from how
> it is referred to in `docs/sprint-plan.md` and in the code, not from Chapter 4
> itself, which is not in this repository. Please check each description against
> your own text. Six requirements — **FR-11, NFR-04, DR-02, DR-03, IR-05,
> IR-07** — are referenced nowhere in the repository, so their rows are blank
> and need your wording before they can be traced.

**Status** is one of: **Done** (implemented, tested and evidenced), **Partly**
(some of it exists; the gap is named), **Not implemented**, or **Text needed**.

Paths are relative to the repository root. Test counts are from the run recorded in `docs/test-results.xml`: **363 Python tests, all
passing** (2026-10-25, with a database available, so the 39 database-backed tests ran).
The interface adds 31 component tests and 9 end-to-end tests, the latter run in both
Chromium and WebKit for 18 runs in total (`docs/evidence/e2e_browsers.txt`).

## Functional requirements

| ID | Requirement | Status | Implemented in | Tests | Evidence |
|---|---|---|---|---|---|
| FR-01 | Worker submits a profile | **Done** | `apps/web/app/worker/profile/page.tsx`; `POST /workers`, `GET /workers/me` in `apps/api/.../app.py`, `service.py: create_worker`, `data/store.py: PostgresProfileStore.save_worker` | `tests/test_api.py` (validation), `tests/test_api_db.py: test_a_stored_worker_can_then_be_recommended_for`, `apps/web/e2e/core-workflow.spec.ts` | `docs/evidence/screens/*/03-create_worker_profile_view.png` |
| FR-02 | Client submits a job posting | **Done** | `apps/web/app/client/post/page.tsx`, `client/postings/page.tsx`; `POST /jobs`, `GET /jobs` in `app.py`, `service.py: create_job`, `store.py: save_job` | `tests/test_api.py` (validation), `tests/test_api_db.py: test_a_posted_job_joins_the_candidate_pool…`, e2e | `docs/evidence/screens/*/07-job_posting_creation.png`, `08-job_posted_confirmation.png`, `09-client_postings_list.png` |
| FR-03 | Profile enrichment: original terms mapped to ESCO concepts | **Done** | `packages/knowledge-graph/src/kaziforce_kg/enrichment.py: ProfileEnricher` | `tests/test_enrichment.py` (12) | `docs/evidence/enrichment_example.md`: 64/64 development known-alias profiles reach their true ESCO occupation |
| FR-04 | Related skills added from the knowledge graph | **Done** | `enrichment.py: ProfileEnricher._infer`, using `graph.py: KnowledgeGraph.skills_of` | `tests/test_enrichment.py: test_known_alias_maps_to_its_occupation_and_essential_skills`, `test_every_inferred_skill_carries_its_full_graph_path` | `docs/evidence/enrichment_example.md`: *fundi wa umeme* → electrician → 21 essential skills, each with its path |
| | *FR-03 and FR-04 are referenced together in the sprint plan; please confirm which is the mapping and which the expansion.* | | | | |
| FR-05 | Rule-based scoring on skill overlap, location, budget/rate and availability | **Done** | `apps/api/.../matching/rule_based.py: RuleBasedScorer` | `tests/test_rule_scorer.py` (32) | `docs/scoring-policy.md` §1; `results/dev/20261017-132422_6698b8a/metrics.md` (`rule_only`, `rule_kg`) |
| FR-06 | Semantic scoring with all-MiniLM-L6-v2 and cosine similarity | **Done** | `matching/semantic.py: SemanticScorer` (revision pinned) | `tests/test_semantic_scorer.py` (4, plus one with the real model marked `slow`) | `docs/scoring-policy.md` §3; `metrics.md` (`semantic_only`, `semantic_kg`) |
| FR-07 | Hybrid score: α·rule + β·semantic, exposing both components | **Done** | `matching/hybrid.py: HybridScorer`, `combine()` | `tests/test_hybrid.py` (4) | `docs/scoring-policy.md` §4; `metrics.md` (`hybrid_no_kg`, `full`) |
| FR-08 | Ranked top-K results with their scores | **Done** | `apps/api/.../pipeline.py: Recommender.rank`; `POST /recommend`; `apps/web/app/worker/matches/page.tsx` | `tests/test_pipeline.py` (8), `tests/test_api.py`, e2e | `docs/evidence/screens/*/04-job_matches_for_worker_view.png`, `06-no_matches.png`, `docs/evidence/demo_run.txt` |
| FR-09 | Explanation for each recommendation: matched skills, the vocabulary mapping used, criterion status, semantic contribution | **Partly** | The data exists and is shown: `MatchedSkill.graph_path` and `source` (`data/models.py`), per-criterion scores (`rule_based.py`), rendered by `apps/web/components/Explanation.tsx` and composed into plain words by `apps/web/lib/explanation.ts`. **Missing:** the specified backend `ExplanationGenerator` producing structured JSON and readable text — `apps/api/.../explainability/explain.py` is still a stub that raises `NotImplementedError` | `apps/web/__tests__/Explanation.test.tsx`, `apps/web/__tests__/explanation.test.ts`, e2e explanation test | `docs/evidence/screens/*/05-worker_explanation_view.png` shows a full path: *fundi wa umeme* → maps to → electrician → has essential skill → install electricity sockets → required by → this job |
| FR-10 | Terms not in the vocabulary are retained, not dropped | **Done** | `enrichment.py`: unmapped entries kept as `text:` skills and listed in `Enrichment.unmapped`; shown by `apps/web/app/worker/matches/page.tsx` as "No strong matches yet" when nothing is reached | `tests/test_enrichment.py: test_unmapped_entries_are_retained_as_text`, `test_no_development_held_out_worker_enriches_to_an_occupation`; e2e FR-10 test | `docs/evidence/enrichment_example.md`: 24/24 held-out profiles keep their alias as unmapped text |
| FR-11 | *(not referenced anywhere in the repository)* | **Text needed** | — | — | — |

## Non-functional requirements

| ID | Requirement | Status | Implemented in | Tests | Evidence |
|---|---|---|---|---|---|
| NFR-01 | Top-K results within 5 seconds | **Done** | `pipeline.py: Recommender`; job embeddings computed once at startup (`service.py`) | Timing recorded per query by `evaluation/evaluator.py` | `results/dev/.../metrics.md`: median 3–35 ms, p95 ≤ 51 ms, maximum 174 ms per query over 216 queries × 7 configurations. **Startup is separate**: about 27–30 s once per process, reported on its own |
| NFR-02 | Explanations for at least 85% of top-K recommendations | **Not implemented** | — | — | No coverage figure is computed. Needs a script over the top-K of a run; belongs with FR-09 |
| NFR-03 | Components are separable modules | **Done** | Abstract interfaces: `kaziforce_kg/enrichment.py: Enricher`, `matching/base.py: Scorer`, `data/store.py: ProfileStore`. A configuration is an (enricher, scorer) pair in `pipeline.py: CONFIGURATIONS`, with no conditional logic inside the scorers | `tests/test_enrichment.py: test_both_enrichers_realise_the_same_interface`, `tests/test_pipeline.py: test_every_configuration_is_an_enricher_scorer_pair`, `test_kg_ablation_pairs_differ_only_in_the_enricher` | The knowledge-graph ablation in `metrics.md` is only possible because the parts are swappable |
| NFR-04 | *(not referenced anywhere in the repository)* | **Text needed** | — | — | — |
| NFR-05 | Works in Chrome and Safari | **Done** | `apps/web` | `apps/web/e2e/core-workflow.spec.ts`, run in Chromium and WebKit (`playwright.config.ts`) | `docs/evidence/e2e_browsers.txt`: 9 tests pass in each of the two engines, 18 in total; `docs/evidence/screens/{chromium,webkit}/` |

## Data requirements

| ID | Requirement | Status | Implemented in | Tests | Evidence |
|---|---|---|---|---|---|
| DR-01 | Profile fields *(referenced as "DR-01/02/05 fields"; exact wording needed)* | **Partly** | `data/synthetic.py` generates biography, skills, location, availability, rate and experience; `data/models.py: WorkerProfile`, `JobPosting` | `tests/test_synthetic_dataset.py`, `tests/test_data_loader.py` | `data/raw/synthetic/manifest.json`, `data/raw/synthetic/README.md` |
| DR-02 | *(not referenced separately)* | **Text needed** | — | — | — |
| DR-03 | *(not referenced anywhere in the repository)* | **Text needed** | — | — | — |
| DR-04 | Missing fields are handled | **Done** | `matching/rule_based.py`: a criterion is scored only when the field is present on both sides; absent criteria are dropped and the remaining weights renormalised | `tests/test_rule_scorer.py: test_renormalisation_drops_absent_criteria`, `test_distractor_is_scored_on_skills_alone`, `test_minimal_worker_is_scored_on_skills_and_location` | `docs/scoring-policy.md` §1 (fixed before any score existed); the interface shows "Not assessed", never 0 (`apps/web/__tests__/Explanation.test.tsx`) |
| DR-05 | Synthetic profiles for cold-start and informal-terminology scenarios | **Done** | `data/synthetic.py` (generator v2, seed 42) | `tests/test_synthetic.py` (8), `tests/test_synthetic_dataset.py` (12) | `data/raw/synthetic/`: 156 groups, 528 worker rows, 280 postings; `manifest.json`; `difficulty_report.md` |
| DR-06 | Evaluation results written to CSV | **Done** | `evaluation/report.py: write_run` | `tests/test_evaluation.py` (6), `tests/test_metrics.py` (13) | `results/dev/20261017-132422_6698b8a/metrics.csv`, `per_query.csv`, `run.json` |
| DR-07 | No personally identifying information | **Done, with one caveat** | `data/synthetic.py` generates no identifiers; `app.py: parse_worker` accepts no name or contact field; `clean_profile_text` strips emails, URLs and phone numbers from the third-party corpus | `tests/test_loaders.py` (18), `tests/test_synthetic_dataset.py: test_distractors_are_cleaned_and_contain_no_contact_details`, `tests/test_vocabulary.py: test_usage_evidence_has_only_the_agreed_fields_and_no_contact_details`, e2e checks the form has no name field | `data/raw/synthetic/README.md`; `docs/evidence/screens/*/03-create_worker_profile_view.png`. **Caveat:** sign-in keys an account by a real phone number, which is personal data. It is never shown to another user and is returned only to its owner, but it is stored in clear as the lookup key — `docs/limitations.md` item 30 |

## Interface requirements

| ID | Requirement | Status | Implemented in | Tests | Evidence |
|---|---|---|---|---|---|
| IR-01 | Web interface for workers and clients | **Done** | `apps/web` (eight routes, built to the eight approved designs in `docs/UI views/`) | 31 component tests, 9 end-to-end tests in each of two engines | `docs/evidence/screens/` |
| IR-02 | Flask REST API exchanging JSON | **Done** | `apps/api/.../app.py`: `GET /health`, `POST /recommend`, `POST /workers`, `POST /jobs`, `GET /jobs/{id}` | `tests/test_api.py` (49), `tests/test_api_db.py` (6) | `docs/api.md` |
| IR-03 | Embeddings stored and queried in pgvector | **Not implemented** | Embeddings are cached in memory only (`matching/semantic.py`). The extension is installed in the database but no vector column exists | — | Deliberate: unnecessary at 280 postings, deferred to backlog issue #45. Recorded in `docs/limitations.md` and `docs/sprint-2-status.md` |
| IR-04 | Knowledge graph query interface: neighbours and a labelled path between nodes | **Done** | `kaziforce_kg/graph.py: KnowledgeGraph` (`find_terms`, `find_occupations`, `skill_by_label`, `occupation_of`, `skills_of`, `path`, `stats`) | `tests/test_kg_graph.py` (16), `tests/test_kg_withheld.py` (14) | `docs/evidence/kg_stats.md`: 544 nodes, 901 edges; paths shown in `docs/evidence/screens/*/05-worker_explanation_view.png` |
| IR-05 | *(not referenced anywhere in the repository)* | **Text needed** | — | — | — |
| IR-06 | Error handling and timeouts | **Partly** | **Error handling: done.** Every route answers one JSON shape — 400 `invalid_request` naming the field, 401, 403, 404, 405, 409, 423, 501, 503 `not_ready` with `Retry-After`, 500 without a stack trace (`app.py`). The client retries a 503 for up to 90 s and reports an unreachable API (`apps/web/lib/api.ts`). **Timeouts: not implemented.** No request or model timeout is set on the server | `tests/test_api.py` error tests, `apps/web/__tests__/api.test.ts` (5) | `docs/api.md` error table |
| IR-07 | *(not referenced anywhere in the repository)* | **Text needed** | — | — | — |

## Summary

| Status | Count | IDs |
|---|---|---|
| Done | 18 | FR-01–FR-08, FR-10, NFR-01, NFR-03, NFR-05, DR-04–DR-07, IR-01, IR-02, IR-04 |
| Partly | 3 | FR-09 (no backend generator), DR-01 (wording to confirm), IR-06 (no timeouts) |
| Not implemented | 2 | NFR-02 (explanation coverage), IR-03 (pgvector, deferred to #45) |
| Text needed | 6 | FR-11, NFR-04, DR-02, DR-03, IR-05, IR-07 |

The three gaps worth closing next are **FR-09** (the explanation generator),
**NFR-02** (which depends on it), and **IR-06**'s timeout half. IR-03 is a
deliberate deferral, recorded as such.
