# KaziForce Compressed Sprint Plan (Sprints 2–6)

> **⚠ Revisit when the real date is known.** The submission and defense date is still being confirmed with the supervisor. This plan assumes **Nov 15, 2026** as the end of the protected buffer. If the real date is earlier, re-cut using §9 before the buffer is touched.

Prepared 2026-10-02 from a Scrum Master view for a solo developer. No BMAD Scrum Master persona is installed, so the plan follows the proposal's own Scrum framing (§3.4). Scope source of truth: `docs/proposal/kaziforce-proposal.docx`, Ch. 3 (methodology, data, model training, validation) and Ch. 4 (FR/NFR/DR/IR).

## 1. Timeline

| Sprint | Window | Theme | Exit increment |
|---|---|---|---|
| 1 | done (PR #7 merged to `dev`) | Data prep & environment | ESCO subset, schema migrations, synthetic stub, wireframes |
| 2 | Oct 1–7 | Data acquisition & preprocessing | Frozen vocabulary, processed corpus, frozen synthetic dataset + ground truth |
| 3 | Oct 8–14 | KG construction & rule-based matching | NetworkX KG, enrichment, rule-based + keyword baseline, eval harness |
| 4 | Oct 15–21 | Semantic embedding & hybrid scoring | MiniLM embeddings, tuned hybrid, Flask API, core-experiment dry run |
| 5 | Oct 22–28 | Explainability & interface | Explanations, Next.js UI end-to-end |
| 6 | Oct 29–Nov 4 | Evaluation & documentation | Final test-split results, core experiment, results chapter drafted |
| Buffer | **Nov 5–15** | Refinement, final docs, defense prep | **Protected: no spillover, no new work** |

Each window runs Thursday to Wednesday, so each one contains one weekend.

## 2. Working model

**Capacity.** About 2 focused hours on most weekdays, plus longer and more flexible blocks on weekends. Tasks are sized to fit that pattern, not an hour budget:

- **S** fits one weekday session.
- **M** takes 2–3 weekday sessions, or part of a weekend.
- **L** needs a weekend block, because it requires sustained focus (design + build + debug).

Plan each window so its **L** task lands on that weekend and the weekday sessions take the S/M tasks.

**Priority tiers within each sprint.**

- **Must** items are on the critical path. The next sprint's Must items depend on them.
- **Should** items are planned for this window but may spill.
- **Stretch** items are done only if the sprint finishes early. Each one becomes a separate issue labelled `stretch`.

**Spillover rule.**

- A sprint may run a few days into the next window.
- Next-sprint work that doesn't depend on the unfinished items can start in parallel.
- A sprint's **Must** items must be done before the next sprint's dependent Must items start.
- Spillover accumulates. If Sprint *N* is still open when Sprint *N+2*'s window starts, stop and re-cut using §9 rather than carrying three sprints at once.
- **Hard boundary:** Sprint 6 ends Nov 4. Nothing spills into Nov 5–15. If Sprint 6 overruns, cut using §7's order.

**Other rules.**

- **Vertical slice first.** By the end of Sprint 4, one worker→job ranking must work through the API, even if crude.
- **No circular evaluation.** Ground-truth relevance labels are defined independently of the recommender and frozen in Sprint 2 (proposal Model Validation section; `docs/ToDo.md` Phase 6). Never edit labels after seeing results.
- **Protect the core claim early.** The Kenyan-terminology / cold-start experiment is the project's central evidence. Its data is built in Sprint 2, it gets a dry run on the validation split in Sprint 4, and Sprint 6 is only the final run.
- **Write as you go.** Each sprint ends with a short implementation note in `docs/notes/` so the thesis chapters are assembled from notes, not written from scratch in Sprint 6.
- **Sprint-end checkpoint** (replaces formal ceremonies): about 30 minutes at the window's end. Compare the demo with the exit criteria, record cuts and spillover, and pick the next sprint's Must items. Send the supervisor a short update after Sprints 3 and 5.
- **Branching and release.** Each sprint's work goes on `sprint-N/<theme>` → PR into `dev` (merge commit). When a sprint's exit criteria are met, merge `dev` → `main` and tag it `sprint-N-done`, so `main` always reflects a stable, demo-able state and a known-good rollback point. Don't merge `dev` into `main` mid-sprint. If a sprint spills, `main` waits until its Must items are done.

## 3. Sprint 2: Data Acquisition & Preprocessing (Oct 1–7)

**Goal:** All data the later sprints depend on exists, is clean, and is frozen.
**Starting state:**
- ESCO subset downloaded (128 occupations, 1,821 skills, 4,746 relations).
- Job Skill Set present (1,167 formal white-collar postings).
- Synthetic generator is a stub (12 workers, 12 jobs).
- `data/vocabulary/` holds candidate terms, none validated.

| ID | Tier | Size | Task | Acceptance criteria |
|---|---|---|---|---|
| S2-1 | Must | S | Merge Sprint 1 PR (#7); branch `sprint-2/data-acquisition`; merge `dev` → `main` (PR #2) as the Sprint 1 release | ✅ PR #7 merged, branch created; PR #2 merged and tagged `sprint-1-done` |
| S2-2 | Must | S | Send vocabulary-validation requests to reviewers **on day 1** | Requests sent; reviewer and deadline (Oct 5) noted in the issue |
| S2-3 | Must | S | Select 10–12 informal occupational areas from the ESCO subset | List in `data/vocabulary/README.md`; each area linked to ≥1 ESCO occupation URI |
| S2-4 | Must | L | Build Kenya-specific vocabulary: ≥5 informal terms per area, mapped informal term → ESCO occupation → skills | Vocabulary file with columns term, register (Swahili/Sheng/English), esco_uri, validation status, note; ≥50 terms |
| S2-5 | Must | M | Validation pass: reviewer spot-check (≥20% sample) or, if no response by Oct 5, a two-published-source check | Validation log committed; **vocabulary frozen** (tag `vocab-v1`); limitation recorded if self-validated |
| S2-6 | Must | L | Expand synthetic generator from the frozen vocabulary: ~100+ workers and ~60+ jobs, seeded. Each occupation gets **formal-English, informal-term, and mixed** descriptions plus **sparse "cold-start" variants** with minimal fields. Include location, availability, and rate/budget. | Deterministic `load_synthetic_data(regenerate=True)`; DR-01/02/05 fields; no PII (DR-07); variant type stored as a column (needed by the core experiment) |
| S2-7 | Must | M | Independent ground-truth rules (occupation/skill/location/availability/budget compatibility, graded 0/1/2) and generated labels | `data/processed/ground_truth.*`; rules documented in `docs/ground-truth.md`; derived from generator specs, never from any scorer |
| S2-8 | Must | S | 70/15/15 split, stratified by occupation and variant type, seeded | Split files + seed committed; **test split untouched until Sprint 6**; tag `data-v1` |
| S2-9 | Should | M | Finish `preprocess_jobs()` for Job Skill Set: clean, dedupe, map skills to ESCO where possible, keep unmapped skills as text | Processed file + row/mapping report; tests |
| S2-10 | Should | S | Record Job Skill Set's role in `data/README.md`: supplementary/negative pool, not primary evaluation jobs | Paragraph committed (approved cut) |
| S2-11 | Should | S | Load synthetic + processed data into PostgreSQL via migrations | Row counts match; repeatable script. Can spill into Sprint 3 |
| S2-12 | Should | S | Sprint note: `docs/notes/sprint-2.md` (vocabulary method, validation outcome, dataset stats) | Committed |

**Exit:** tags `vocab-v1` and `data-v1` exist. Sprint 3's KG and evaluation work depends on S2-3…S2-8.
**May spill:** S2-9, S2-11 (Sprint 3 can start on ESCO + synthetic data without them).
**Approved cuts applied:** 10–12 areas instead of 15–20; Job Skill Set demoted.
**Risk:** Vocabulary validation depends on other people, so start it immediately (S2-2). The self-validation fallback is pre-agreed so this sprint can't stall on it.

## 4. Sprint 3: KG Construction & Rule-Based Matching (Oct 8–14)

**Goal:** A working knowledge graph and enrichment, a rule-based scorer, a keyword baseline, and an evaluation harness that already produces baseline numbers.

| ID | Tier | Size | Task | Acceptance criteria |
|---|---|---|---|---|
| S3-1 | Must | L | KG builder in `packages/knowledge-graph`: ESCO backbone, plus informal-term nodes with `maps_to` edges, plus worker/job/location nodes | Entity types per proposal; consistency checks (duplicates, invalid skill IDs, missing fields); graph stats printed |
| S3-2 | Must | M | Enrichment component (FR-03, FR-04, FR-10): profile → original terms + mapped ESCO concepts + related skills; unmapped terms retained | Separable module (NFR-03); unit tests including an unmapped-term case |
| S3-3 | Must | S | KG query interface (IR-04): neighbours and labelled path between two nodes | Used later by explanations; tests |
| S3-4 | Must | M | Rule-based scorer (FR-05): skill overlap, location, budget/rate, availability; missing fields handled per DR-04 | Returns score + per-criterion breakdown; tests |
| S3-5 | Must | S | Keyword baseline: skill-keyword overlap, no KG, no semantics | Same scorer interface |
| S3-6 | Must | M | Evaluation harness: Precision@K, MRR, per-config runner, results to CSV (DR-06), sliceable by variant type | Keyword vs. rule-based (± KG) numbers on the **validation split** |
| S3-7 | Should | S | Sprint note + supervisor update | `docs/notes/sprint-3.md`; update sent |
| S3-8 | Stretch | S | KG visualisation figure for thesis (pyvis/matplotlib) | PNG in `docs/figures/`; otherwise deferred to buffer as a non-code task |

**Exit:** One command prints P@K and MRR for keyword vs. rule-based, with and without KG enrichment, on validation data.
**May spill:** S3-7 only. The harness (S3-6) is Must because Sprint 4 tuning depends on it.
**Simplifications (already within proposal scope):** ESCO subset only; NetworkX in memory, rebuilt at API start-up; no graph database.
**Risk:** If KG enrichment doesn't lift rule-based scores on validation, investigate vocabulary coverage. Never adjust labels.

## 5. Sprint 4: Semantic Embedding & Hybrid Scoring (Oct 15–21)

**Goal:** A semantic component and a tuned hybrid behind a Flask API (the vertical slice), plus a dry run of the core experiment.

| ID | Tier | Size | Task | Acceptance criteria |
|---|---|---|---|---|
| S4-1 | Must | M | Semantic scorer (FR-06): all-MiniLM-L6-v2 embeddings of enriched text, cosine similarity, embeddings cached; timeout/error handling (IR-06) | Tests; embeddings computed once |
| S4-2 | Must | M | Store and query embeddings in pgvector (IR-03). **Timeboxed to one weekend.** If not working by **Oct 18**, fall back to a NumPy cache + Postgres for relational data and log it as a thesis deviation. | Either path returns the same top-N on a sample |
| S4-3 | Must | S | Hybrid scorer (FR-07): `α·rule + β·semantic` (Eq. 3.1) on normalised components, exposing component scores | Tests |
| S4-4 | Must | M | Tune α/β on the **validation split** only, with a sensitivity table | Chosen weights + table recorded; test split unused |
| S4-5 | Must | S | All five configs in the harness: keyword, rule, semantic, hybrid−KG, hybrid+KG | Validation results CSV |
| S4-6 | Must | S | **Core-experiment dry run** on validation: configs sliced by formal / informal / mixed / cold-start variants | Table produced. Confirms the S6 experiment works end to end, and early warning if the data doesn't support the claim |
| S4-7 | Must | L | Flask REST API (IR-02): `POST /workers`, `POST /jobs`, `GET /workers/{id}/matches`, `GET /jobs/{id}/matches`; JSON; validation and 4xx errors | API tests; `curl` returns ranked matches with component scores |
| S4-8 | Should | S | Latency check against NFR-01 (<5 s) | One timing number logged |
| S4-9 | Should | S | Next.js + TypeScript scaffold in `apps/web` with an API client calling `/health` | Runs locally. Can slip to the start of Sprint 5 |
| S4-10 | Should | S | Sprint note | `docs/notes/sprint-4.md` |

**Exit:** A worker ID returns ranked jobs with component scores via the API; five configs and the variant-sliced dry run exist on validation data.
**May spill:** S4-8…S4-10.
**Simplifications:** Pre-trained MiniLM only, no fine-tuning; no authentication; no ANN index.

## 6. Sprint 5: Explainability Module & Interface (Oct 22–28)

**Goal:** Every recommendation carries a traceable explanation, and the full flow works in the browser.

| ID | Tier | Size | Task | Acceptance criteria |
|---|---|---|---|---|
| S5-1 | Must | L | Template-based explanation generator (FR-09): matched skills, vocabulary mapping used, location/budget/availability status, semantic contribution. Each item references a KG path or score component. | Structured JSON + readable text; handles unmapped terms, missing fields, and no KG path without failing (FR-10) |
| S5-2 | Must | S | Explanation coverage + traceability script (NFR-02, ≥85%) | Coverage figure on validation top-K |
| S5-3 | Must | S | API returns `explanation` with each match | Contract documented in `apps/api` README |
| S5-4 | Must | M | UI: worker profile form + job posting form (FR-01, FR-02), per wireframes 01–02 | Validation and error display |
| S5-5 | Must | M | UI: ranked top-K results + explanation view (FR-08, FR-09), per wireframes 03–04 | Loading and error states; score breakdown shown |
| S5-6 | Must | S | End-to-end smoke test (submit → match → explanation) in Chrome and Safari (NFR-05) | Checklist run; defects logged |
| S5-7 | Should | S | Sprint note + supervisor update (screen recording is fine) | Committed / sent |
| S5-8 | Stretch | S | Show the KG path visually in the explanation view | Otherwise text only |

**Exit:** The complete demo flow works from the browser locally.
**May spill:** S5-7 and minor UI polish, but only until about Oct 31. Sprint 6 needs the system feature-frozen.
**Approved cuts applied:** template-based explanations (no LLM); Chrome + Safari only; no deployment (a recorded demo is made in the buffer as the defense fallback).

## 7. Sprint 6: Evaluation & Documentation (Oct 29–Nov 4)

**Goal:** Final numbers on the untouched test split, the core experiment, testing evidence, and a drafted results chapter, so the buffer is for polish only. **No spillover past Nov 4.**

| ID | Tier | Size | Task | Acceptance criteria |
|---|---|---|---|---|
| S6-1 | Must | M | Final evaluation on the **test split**: all five configs, P@K and MRR | Results CSV + commit hash recorded; Sprint 4 weights unchanged; run once |
| S6-2 | Must (**protected**) | L | **Kenyan-terminology / cold-start experiment** on the test split: configs compared on formal vs. informal vs. mixed vs. cold-start profiles (Objective v, the central claim) | Results tables + interpretation drafted |
| S6-3 | Must | S | Explanation coverage/traceability on the test split (NFR-02) | Table |
| S6-4 | Must | M | Draft results, implementation and limitations sections from the sprint notes | Draft ready for supervisor review. Limitations: synthetic data, Job Skill Set caveat, vocabulary validation, single seeded run |
| S6-5 | Should | S | Response time (NFR-01): N queries, mean/p95 | Table |
| S6-6 | Should | M | Testing evidence: black-box functional checklist; unit + one integration test (web→API→DB) for the critical path | `pytest` green; test table |
| S6-7 | Should | S | Results figures (charts) | `docs/figures/` |
| S6-8 | Should | S | README: setup, run, reproduce; tag `v1.0-submission-candidate` | Fresh-clone run-through works |
| S6-9 | Should | S | Statistical rigour: report P@K at K∈{3,5,10} and per-occupation breakdown | Tables |
| S6-10 | Stretch | S | Bootstrap confidence intervals over queries | CI columns added |

### Sprint 6 cut order (if it overruns)

Cut from the top. The core experiment is last.

1. **S6-10** bootstrap CIs: drop.
2. **S6-9** statistical rigour: reduce to K=5 only, drop per-occupation breakdowns, and if needed replace with a **qualitative pass** (a short discussion of a few example rankings and the limits of a single seeded run). P@K/MRR point estimates from S6-1 remain.
3. **S6-7** charts: present results as tables only.
4. **S6-5** response time: a single representative timing instead of a distribution.
5. **S6-6** testing: reduce to the black-box checklist plus the existing unit tests.
6. **S6-8** README: minimal run instructions; finish the polish in the buffer (documentation is allowed there).
7. **S6-4** drafting: draft results only; implementation and limitations sections move to the buffer's writing days.
8. **S6-3** explanation coverage: report the validation figure from S5-2 instead.
9. **S6-2 Kenyan-terminology / cold-start experiment: never cut.** If it's still at risk after items 1–8, simplify by reducing the variant slices compared (keep formal vs. informal, and cold-start vs. full) rather than dropping it.

**Approved cut applied:** single seeded test run, no significance testing.

## 8. Buffer: Nov 5–15 (protected)

**Allowed:** bug fixes on the frozen system, thesis writing and editing, figures, references, supervisor feedback, slides, demo recording, Q&A rehearsal, submission formatting.
**Not allowed:** spillover from Sprints 2–6, new features, new experiments, re-tuning weights, changing labels.

| Days | Focus |
|---|---|
| Nov 5–8 | Incorporate supervisor feedback; finish documentation and results chapter |
| Nov 9–11 | Defense slides, recorded demo, clean-clone reproduction test |
| Nov 12–13 | Full defense rehearsal; prepare answers on limitations (synthetic data, no partner data, circularity safeguards) |
| Nov 14–15 | Final proof-read, submission package |

## 9. Cuts and simplifications

**Approved (2026-10-02):**

| Original scope | Change | Sprint |
|---|---|---|
| 15–20 informal occupational areas | 10–12 | 2 |
| Job Skill Set as evaluation jobs | Supplementary/negative pool only | 2 |
| Explanations | Template-based, no LLM | 5 |
| Statistical rigour | Single seeded test run; may fall back to a qualitative pass | 6 |
| UI/deployment | Chrome + Safari only, no deployment, recorded demo | 5 / buffer |

**Approved de-risking (2026-10-02):** profile-variant generation (formal / informal / mixed / cold-start) moved into Sprint 2 (S2-6); core-experiment dry run added to Sprint 4 (S4-6).

**Within proposal scope (no approval needed):** NetworkX in memory with no graph DB; pre-trained MiniLM with no fine-tuning; no authentication; cold-start simulated by field removal on synthetic profiles; no real-user study.

**Contingency (not yet triggered):**
- pgvector → NumPy-cache fallback if not working by Oct 18 (deviation from IR-03, to be noted in the thesis).
- If the submission date is earlier than Nov 15, apply §7's cut order across all sprints, starting from Stretch items, then Should items, and keep the protected experiment.

## 10. Issue-creation guide

- One **milestone** per sprint (`Sprint 2` … `Sprint 6`; due Oct 7, 14, 21, 28, Nov 4) plus `Buffer` (Nov 15).
- One **issue** per task ID. Use the task as the title, the acceptance criteria as a checklist, and the tier/size in the body.
- Labels: `sprint-N`, `must` / `should` / `stretch`, `size-S` / `size-M` / `size-L`, area (`data`, `kg`, `matching`, `api`, `web`, `explainability`, `eval`, `docs`), and `protected` for S6-2.
- Put requirement IDs (FR/NFR/DR/IR) in issue bodies for traceability.
- When something spills, move the issue to the next milestone and add a `spillover` label so the retrospective can see the pattern.
