# System test record

**Date run:** 2026-11-12 (00:15–00:45 EAT).

**Build under test:** `dev` at `fd00c45` (PR #63). The record's own commit adds documentation only, so no application code differs.

**Environment:** an isolated copy of the full stack on the development machine (macOS 15.8.1, Intel i5-8279U, 8 GB), so the working database was not touched:
- PostgreSQL 14.19, a scratch UTF-8 cluster on port 5433. Migrations 0001–0005 applied, then `scripts/seed_database.py` (216 workers, 280 postings).
- Flask API on `127.0.0.1:5002`, configuration `full`, display threshold 55.
- Next.js dev server on `127.0.0.1:3002`, Chromium 1280×900.

**Method:**
- Each case was driven through the real interface by a Playwright script: create a client account and post the job, then create a worker account, fill the profile, read the matches, and open an explanation.
- Every account used a generated test number (7xxxxxxxx) and the name "Test Worker". No real personal data was entered.
- **Exact positions came from the database, not the screen.** Several synthetic postings share their title with a case's job (for example, a seeded "Install a new distribution board", Kasarani, KES 3,600, Weekends). For each worker, the rank and composite score of the case's *own* posting were therefore read from the persisted `match_score` rows (FR-11). A second worker with the same profile then opened that posting's explanation by its ID (runs suffixed `s`).
- Which trade each worker reached was read from `POST /recommend` with a typed-in profile, which stores nothing (`docs/evidence/system-tests/api-enrichment.json`).

**Evidence:**
- Screenshots: `docs/evidence/system-tests/` (named `T-NN-<step>.png`).
- Captured screen text: `docs/evidence/system-tests/run-log.json`.

**About the "Expected" lines.** The expectations in each use case were written in advance as informal predictions of what a person would hope to see. They were **not** derived from the scoring policy (`docs/scoring-policy.md`), so a band named in them ("Strong") is a guess, not an acceptance threshold. T-01's own posting scoring 75 (Moderate) is therefore not a failure. A case fails only where the system did something its requirements or its policy say it should not, or failed to do something they say it should.

**Verdicts:** pass · pass with note · fail · constrained (the case as written conflicts with an interface constraint, which is recorded, and a variant within the constraint was run).

**Retest after the pre-freeze fixes (2026-11-12, 01:30–01:35 EAT).** Build `a727bc8`, the same isolated set-up with migrations 0001–0006. T-01, T-04 and T-08a were re-run, and the `match_score` table was checked for S-1. Evidence: `docs/evidence/system-tests/retest-2026-11-12/`.

## Summary

| Case | What it exercises | Verdict |
|---|---|---|
| T-01 | English only; trade reached through the occupation label | pass (retested after S-2: unchanged) |
| T-02 | Swahili term on the worker side, English job | worker side passes; the posted job is not matched, by limitation S-3 |
| T-03 | Fully Swahili worker, English job | worker side passes; the posted job is not matched, by limitation S-3 |
| T-04 | English worker, Swahili job | **failed**, fixed (S-2, `cf644c3`), retested: worker side passes; the posted job is not matched, by limitation S-3 |
| T-05 | Swahili on both sides, two different aliases | pass with note |
| T-06 | Withheld alias, then the one-word contrast | pass |
| T-07 | Missing fields | constrained (a client must give a budget); T-07a passes |
| T-08 | A trade outside the ten areas | constrained (location is a closed list); T-08a passes, retested |

---

## Use cases

The full text of each case is copied from the use-case file (kept outside the repository), so this record stands alone.

### T-01 — English only, baseline

> **Worker.** What work do you do? electrician, electrical installation, wiring, test electrical equipment · About you? Experienced electrician with eight years in residential and commercial installations across Nairobi. · Where? Nairobi - Kasarani · When? Full-time · Rate? 2500
> **Job.** Title: Install a new distribution board · Skills: electrical installation, install electricity sockets, test electrical equipment · Description: Need an electrician to install a new distribution board in a three-bedroom house and test the circuits. · Budget: 2800 · Location: Nairobi - Kasarani
> **Expected:** electrician, via occupation label. Strong. Explanation should cite shared skills, same location, rate within budget.

| Test performed | Expected | Actual | Corrective action |
|---|---|---|---|
| Posted the job as a client, then created the worker and read the matches and the explanation of the posted job | Electrician via occupation label; Strong; the explanation cites shared skills, location and rate | **Trade:** electrician, reached through the occupation label in the biography (API: `occupations: [electrician]`, `terms: []`). The posting was read as electrician, and "electrical installation" was kept as the client wrote it. **Own posting:** rank 4, **score 75, Moderate** (not Strong); ranks 1–3 are seeded electrical postings, the first sharing this title (86, Strong). **Explanation** (`T-01s-6-own-posting-explanation.png`): install electricity sockets ("That's part of electrical work"); test electrical equipment and electrical installation ("You said you do … and this job mentions it"); "You're both in Nairobi - Kasarani"; "Your rate of KES 2,500 a day fits their budget". **Couldn't check:** "This job doesn't say when the work is". | None to the system. The band is lower than expected because the semantic component scored 0.497 for this pair (rule 1.000). The expectation of "Strong" was a guess, not a rule. **Note:** the matches screen shows two postings with the same title; a client cannot tell them apart from the card alone. |

| **Retest** (2026-11-12, after S-2 `cf644c3`): the same worker and job | Unchanged: the biography already named the occupation | **Pass, unchanged.** Electrician reached; own posting rank 4, score 75 (Moderate), read from `match_score`. The worker now also reaches electrician through the listed entry "electrician", which is no longer reported unmapped (`tests/test_enrichment.py::test_t01_worker_reaches_electrician_through_the_occupation_label`). | None. |

Screenshots: `T-01-1-job-posted.png`, `T-01-2-profile-filled.png`, `T-01-3-matches.png`, `T-01s-6-own-posting-explanation.png`, `retest-2026-11-12/R-T-01-3-matches.png`.

### T-02 — Partial Swahili worker, English job

> **Worker.** What work do you do? fundi bomba, pipe fitting, replace faucets · About you? Nina uzoefu wa miaka sita. I handle bathroom and kitchen plumbing in Nairobi. · Where? Nairobi - Kawangware · When? Part-time · Rate? 2200
> **Job.** Title: Fix bathroom leakage · Skills: install sanitary equipment, repair pipes · Description: Looking for a plumber to fix leaking joints in the upstairs bathroom. Materials are on site. · Budget: 2400 · Location: Nairobi - Kawangware
> **Expected:** plumber, via fundi bomba. This is the core claim — Swahili term on one side, English on the other, matched through the graph.

| Test performed | Expected | Actual | Corrective action |
|---|---|---|---|
| As T-01 | Plumber via fundi bomba; the posted job matched through the graph | **Worker side passes:** "You described yourself as a fundi bomba. We matched that to the trade plumber". The top 3 are other plumbing postings (78, 70 and 69, all Moderate), each explained through inferred plumbing skills. **Own posting fails:** rank 24, **score 44, below the threshold, not shown**. Its explanation (`T-02s-6`) lists only location and rate; **no skill is shared.** The client's confirmation screen says "We didn't recognise 'install sanitary equipment', 'repair pipes', so we kept it exactly as you wrote it". | **Cause:** a job's required skills are compared as stated, by exact ESCO label (`docs/scoring-policy.md` §1). Neither entry is an ESCO label (the nearest is "place sanitary equipment"), so they stay literal text that no worker holds. **Not changed, by decision (2026-11-12): a limitation, not a defect** (S-3). It is reported in Chapter 5: vocabulary bridging works for worker terms and for job *terms*, but not for free-text job *skills*. |

Screenshots: `T-02-1-job-posted.png`, `T-02-3-matches.png`, `T-02-3-explanation.png` (rank 1), `T-02s-6-own-posting-explanation.png`.

### T-03 — Fully Swahili worker, English job

> **Worker.** What work do you do? fundi wa mbao · About you? Nimefanya kazi ya useremala kwa miaka kumi. Natengeneza meza, viti na makabati. · Where? Thika · When? Full-time · Rate? 2000
> **Job.** Title: Make school desks · Skills: woodworking, assemble furniture, use woodworking tools · Description: We need a carpenter to build forty school desks from locally sourced timber. · Budget: 2500 · Location: Thika
> **Expected:** carpenter, via fundi wa mbao. No English on the worker side at all, so this is the strongest demonstration of the mapping.

| Test performed | Expected | Actual | Corrective action |
|---|---|---|---|
| As T-01 | Carpenter via fundi wa mbao; the posted job matched | **Worker side passes:** "You described yourself as a fundi wa mbao. We matched that to the trade carpenter". There are 9 carpentry matches (67 to 65, Moderate). **Own posting fails:** rank 15, **score 52, below the threshold.** Its explanation (`T-03s-6`) shows location and rate only; no skill is shared. All three job skills were "not recognised" on the client's screen. (The "Make school desks" card at #4 is a seeded posting in Kitengela.) | The same cause as T-02. None of "woodworking", "assemble furniture" or "use woodworking tools" is an exact ESCO label. Same proposal as T-02. |

Screenshots: `T-03-1-job-posted.png`, `T-03-3-matches.png`, `T-03-3-explanation.png`, `T-03s-6-own-posting-explanation.png`.

### T-04 — English worker, Swahili job

> **Worker.** What work do you do? vehicle technician, engine diagnostics, brake repair · About you? Motor vehicle mechanic with twelve years on saloon cars and light commercial vehicles. · Where? Nairobi - Embakasi · When? Full-time · Rate? 3000
> **Job.** Title: Gari haina nguvu · Skills: makanika, diagnose engine fault · Description: Natafuta makanika wa magari. Gari langu linapoteza nguvu na linatoa moshi. Niko Embakasi. · Budget: 3200 · Location: Nairobi - Embakasi
> **Expected:** the job should map through makanika to vehicle technician, and the English worker should still match. Tests the bridge in the opposite direction.

| Test performed | Expected | Actual | Corrective action |
|---|---|---|---|
| As T-01 | Job → vehicle technician via makanika; the worker matches it | **Job side passes:** "You wrote 'makanika', which is another way of saying vehicle technician". **Worker side fails:** the worker reaches **no occupation** (API: `occupations: []`; all three entries unmapped), and the screen shows **"No strong matches yet"** (best score 45). **Own posting:** score 25, outside the top 10. | **Two causes, both in the code:** (1) **occupation labels are searched only in the biography, never in the "What work do you do?" entries** (`packages/knowledge-graph/src/kaziforce_kg/enrichment.py`, step 3 uses `text` only). T-01 succeeded only because its biography happens to say "electrician"; this biography says "mechanic". (2) The job's stated skills ("makanika", "diagnose engine fault") are kept as text, as in T-02. **(1) fixed in `cf644c3`** (S-2); the development split was re-run and every metric is unchanged (runs `results/dev/20261112-012400_f5587b0` and `results/dev/20261112-012811_cf644c3`; no profile in the dataset lists an occupation's name as a work entry). **(2) is limitation S-3**, by decision. See the retest row below. |

| **Retest** (2026-11-12, after S-2 `cf644c3`): the same worker and job | The worker reaches vehicle technician and sees motor-vehicle matches | **Pass for the worker.** **8 matches**, #1 "Service and repair a saloon car" (68, Moderate), explained through "That's part of motor vehicle repair". **The posted job is still not matched:** rank 22, score 31, because its skills "makanika" and "diagnose engine fault" are kept as text (limitation S-3, by decision). The explanation opened contains a **false location sentence**, "You're both in Nairobi - Embakasi", for a job in Nairobi - Rongai: see S-7. | S-2 fixed. S-3 is recorded as a limitation. S-7 is open. |

Screenshots: `T-04-1-job-posted.png`, `T-04-3-matches.png`, `T-04s-6-own-posting-explanation.png`, `retest-2026-11-12/R-T-04-3-matches.png`, `retest-2026-11-12/R-T-04-3-explanation.png`.

### T-05 — Both sides Swahili

> **Worker.** What work do you do? mpishi, kupika chakula cha Kiafrika · About you? Mimi ni mpishi. Nimefanya kazi hoteli na kwenye sherehe kwa miaka saba. · Where? Nakuru · When? Weekends · Rate? 1800
> **Job.** Title: Mpishi wa harusi · Skills: mpikaji, prepare food, use cooking techniques · Description: Tunahitaji mpishi kwa harusi ya watu mia mbili. Kazi ni siku moja, Nakuru. · Budget: 2000 · Location: Nakuru
> **Expected:** cook on both sides, through two different aliases — mpishi and mpikaji. Both map to the same occupation, which is worth seeing.

| Test performed | Expected | Actual | Corrective action |
|---|---|---|---|
| As T-01 | Cook on both sides, through mpishi and mpikaji | **Pass.** Job: "You wrote 'mpikaji', which is another way of saying cook". Worker: "You described yourself as a mpishi. We matched that to the trade cook". **Own posting:** rank 2, **score 67, Moderate.** Explanation: "This job needs someone to use cooking techniques. That's part of cooking"; same town; rate fits. **Couldn't check:** "This job doesn't say when the work is". | None. **Note:** "prepare food" was not recognised (not an ESCO label), so only one of the three job skills was shared. |

Screenshots: `T-05-1-job-posted.png`, `T-05-3-matches.png`, `T-05-3-explanation.png`.

### T-06 — The withheld alias

> **Worker.** What work do you do? fundi wa stima · About you? Nina uzoefu wa miaka mitano kwa kazi ya stima za nyumba. · Where? Nyeri · When? Full-time · Rate? 2300
> **Job:** reuse T-01's.
> **Expected:** no trade shown, nothing clears 55, "No strong matches yet". The term is real Swahili for an electrician but was deliberately withheld from the graph. Then, for contrast, change only the first field to *fundi wa umeme* and resubmit. Same person, same biography, same location — one word different, and matches appear.

| Test performed | Expected | Actual | Corrective action |
|---|---|---|---|
| Created the worker; read the matches; edited only "What work do you do?" to *fundi wa umeme*, saved, and re-read the matches | No trade; nothing ≥ 55; "No strong matches yet". After the edit, matches appear | **Pass.** With *fundi wa stima*: no occupation (API: `unmapped: ['fundi wa stima']`), **"No strong matches yet"**, best score 43. After the one-word edit: **8 matches**, #1 "Install security lights in a compound" (Nyeri, 71, Moderate). The explanation opened (`T-06-5-contrast-explanation.png`) reads "That's part of electrical work" and "You described yourself as a fundi wa umeme. We matched that to the trade electrician". T-01's own posting scores 49 for this worker (a different town) and is not shown. | None to matching. **Note:** after "Save", the app returns to the profile page rather than to the matches, so the worker has to open "My matches" to see the change. |

Screenshots: `T-06-2-profile-filled.png`, `T-06-3-matches.png`, `T-06-4-contrast-profile.png`, `T-06-5-contrast-matches.png`, `T-06-5-contrast-explanation.png`.

### T-07 — Missing fields

> **Worker.** What work do you do? kinyozi · About you? Barber in Kitengela. Cuts, shaves, beard trims. · Where? Kitengela · When? leave blank · Rate? leave blank
> **Job.** Title: Weekend barber for a busy salon · Skills: barbering techniques, style hair · Description: Need a barber for Saturdays and Sundays at a salon in Kitengela. · Budget: leave blank · Location: Kitengela
> **Expected:** barber via kinyozi. "What we couldn't check" should mention availability and rate — not zeros. Scored on skills and location only, with weights renormalised.

| Test performed | Expected | Actual | Corrective action |
|---|---|---|---|
| T-07 as written: posted the job with the budget left blank | The posting is accepted without a budget | **Interface constraint.** The job form requires a budget: "Budget per day (required)" … "Give a budget per day." (`T-07-error.png`). A client cannot post without a budget, although a worker may omit a rate. | No change. A client's budget is required by design; a worker's rate is optional. The missing-field behaviour this case targets is exercised from the worker side in T-07a, and from the job side by the 200 distractor postings, which carry no budget (`docs/scoring-policy.md` §1). Recorded as an interface constraint (S-4). |
| T-07a: the same, with a job budget of KES 2,000; the worker's rate and availability left blank | Barber via kinyozi; "couldn't check" names rate and availability; no zeros | **Pass.** "You described yourself as a kinyozi. We matched that to the trade barber". **Own posting:** rank 1, **84, Strong.** "What lined up": barbering techniques; style hair; "You're both in Kitengela". **"What we couldn't check":** "You haven't given a daily rate, so we couldn't compare it with their budget." and "You haven't said when you can work, so we couldn't check that." No zero is shown. | None. |

Screenshots: `T-07-error.png`, `T-07a-1-job-posted.png`, `T-07a-3-matches.png`, `T-07a-3-explanation.png`.

### T-08 — Outside the ten areas

> **Worker.** What work do you do? welder, arc welding, metal fabrication · About you? Welder with six years making gates, grilles and steel doors. · Where? Nairobi - Industrial Area · When? Full-time · Rate? 2600
> **Job:** reuse any of the above.
> **Expected:** no trade, no inferred skills, the terms kept as plain text. Probably "No strong matches yet". This is a scope limitation (you didn't cover welding), distinct from T-06's coverage limitation (you cover electricians but not that word).

| Test performed | Expected | Actual | Corrective action |
|---|---|---|---|
| T-08 as written | The location can be entered | **Interface constraint.** "Where do you work?" is a fixed list of 20 places; "Nairobi - Industrial Area" is not among them (`T-08-error.png`). The comment in `apps/web/lib/locations.ts` says "The field accepts any text", which is true of the API but not of the form. | No change to the list. The misleading comment was corrected in **`a727bc8`**. Recorded as an interface constraint (S-5). The location does not affect what T-08 tests (no trade for an uncovered occupation), so T-08a uses a listed Nairobi area. |
| T-08a: the same, with "Nairobi - Embakasi" | No trade, no inferred skills, terms kept as text; "No strong matches yet" | **Pass.** API: `occupations: []`, `terms: []`, `unmapped: ['welder', 'arc welding', 'metal fabrication']`. Screen: **"No strong matches yet"** (best score 41). | None. |

| **Retest** (2026-11-12, after S-2): T-08a again | Unchanged: an entry naming no occupation must still reach none | **Pass.** "No strong matches yet"; welder entries still unmapped (`tests/test_enrichment.py::test_an_entry_that_names_no_occupation_is_still_unmapped`). | None. |

Screenshots: `T-08-error.png`, `T-08a-2-profile-filled.png`, `T-08a-3-matches.png`, `retest-2026-11-12/R-T-08a-3-matches.png`.

---

## Defects found while running these tests

| # | Test performed | Expected | Actual | Corrective action |
|---|---|---|---|---|
| S-1 | After the runs, counted the `match_score` rows per test worker in the scratch database | One current ranking per worker and configuration: `POST /recommend` deletes the previous ranking before inserting (FR-11, `33df7f5`) | **Duplicate rows.** Workers who opened an explanation have 100 rows for 50 distinct postings. The API log shows `/recommend` calls arriving in pairs within the same second, which is consistent with React running each page's effect twice in development. The delete-then-insert in `PostgresProfileStore.save_match_scores` is not serialised per worker. Two transactions each delete nothing, then both insert. The ranking persisted is also whichever request came last: K = 10 from the matches screen, or K = 50 from the explanation screen | **Fixed in `f5587b0`.** `save_match_scores` takes a transaction-scoped advisory lock per (worker, configuration), then deletes and upserts. Migration 0006 removes existing duplicates (keeping the newest row) and adds `UNIQUE (fk_worker_id, fk_posting_id, configuration)`. The evaluation is unaffected: it never reads the database (IR-07). |
| S-1 retest (automated) | Four threads replace one worker's ranking at once with K = 5 and K = 8, five rounds (`tests/test_store.py::test_concurrent_replacements_leave_exactly_one_ranking`); two concurrent `POST /recommend` calls, five rounds (`tests/test_api_db.py::test_two_concurrent_requests_for_matches_leave_one_ranking`); a duplicate insert (`test_the_database_refuses_a_second_row_for_the_same_pair`); 0006 applied over existing duplicates (`tests/test_match_score_migration.py`) | Exactly one ranking (ranks 1..n, n distinct postings); the duplicate refused; 0006 keeps the newest row | **Before the fix:** 26 rows and 20 rows where one ranking of 5 or 8, and of 10, was expected; no duplicate refused. **After:** all four pass. Full suite: 509 passed. | — |
| S-1 retest (in the app) | Re-ran T-01, T-04 and T-08a through the browser; counted `match_score` rows per test worker | One ranking per worker, even though the pages still send two requests at once | `/recommend` calls still arrive in pairs (API log). **Rows: 50 for 50 distinct postings, 50 for 50, 10 for 10. No duplicates.** (50 because the explanation screen asks for K = 50, and the last request's ranking is the one kept.) | — |
| S-2 | T-04 | A worker who writes an occupation's English name in "What work do you do?" reaches that occupation | It did not. Occupation labels were matched in the biography only | **Fixed in `cf644c3`.** Labels are now looked for in each listed entry as well as in the text; an entry naming an occupation is no longer reported unmapped. |
| S-2 retest | Unit tests with T-01's and T-04's worker inputs verbatim, plus three edge cases (`tests/test_enrichment.py`); T-04 and T-01 re-run in the browser; development split re-run | T-04's worker reaches vehicle technician; T-01 unchanged; an entry naming no occupation stays unmapped | **Before the fix:** 3 of the 5 new tests failed. **After:** all pass. T-04's worker gets 8 matches (was "No strong matches yet"); T-01 unchanged. Development split: **every metric identical** before and after (runs `20261112-012400_f5587b0`, `20261112-012811_cf644c3`), because no dataset profile lists an occupation's name. | — |
| S-3 | T-02, T-03, T-04 | A client's free-text skill reaches the matching vocabulary | Only an exact ESCO label does. Anything else stays literal text, and the screen says so | **Not a defect: a limitation, by decision (2026-11-12)** (`scoring-policy.md` §1). Reported in Chapter 5. See T-02. |
| S-4 | T-07 | A job can be posted without a budget | The form requires a budget | **Interface constraint, kept.** See T-07. |
| S-5 | T-08 | Any location can be entered | Only 20 listed places | **Interface constraint, kept.** The code comment that claimed otherwise was corrected in **`a727bc8`**. |
| S-6 | Setting up the scratch database for this run | `python -m kaziforce_api.data.migrate` applies cleanly to a new database | It failed with `UnicodeEncodeError: 'ascii' codec can't encode character '—'` when the cluster had been created with the default SQL_ASCII encoding. The migration files contain an em dash | **Fixed in the setup instructions, `a727bc8`:** the README now states that the database must be UTF-8, how to check it, and how to create it (`createdb -E UTF8 -T template0`). **Retest:** on a fresh default cluster (`SQL_ASCII`), a database created that way applied migrations 0001–0006 cleanly. |
| S-7 | T-04 retest: opened the explanation for "Service and repair a saloon car" (job in Nairobi - Rongai; worker in Nairobi - Embakasi) | A location sentence appears only when the places match, and states what is true | "**You're both in Nairobi - Embakasi.**" The location criterion scores 0.5 for the same town, and `ExplanationGenerator` writes "You're both in {the worker's location}" for **any** score above zero (`explainability/explain.py`, `CRITERION_PHRASE`, `_criterion_reasons`) | **Open, not fixed: found after the agreed scope for these fixes.** Needs a decision before the freeze. It changes explanation text only; no score, ranking or NFR-02 coverage figure (the strict rule needs a shared skill). |
| S-8 | Typed-in plumber, rate KES 3,000, against postings with smaller budgets (`POST /recommend`, K = 50) | A budget sentence appears only when the rate is within the budget | "**Your rate of KES 3,000 a day fits their budget.**" for budgets of KES 2,200, 2,600 and **1,800** (`budget_fit` 0.64, 0.85, 0.33). Any `budget_fit` above zero produces the sentence, and the policy gives a partial score to rates above budget (`scoring-policy.md` §1). **The committed evidence contains the same false sentence:** `docs/evidence/explanation_payload.md` (rate KES 2,000, budget KES 1,400, `budget_fit` 0.57) | **Open, not fixed: as S-7.** |

## Defects found earlier, with the failing state visible in history

| # | Test performed | Expected | Actual | Corrective action |
|---|---|---|---|---|
| H-1 | Opened the interface at `127.0.0.1:3000` instead of `localhost:3000` (2026-10-20) | Requests succeed from either spelling of the local address | Every request failed. The API allowed exactly one origin: `DEFAULT_CORS_ORIGIN = "http://localhost:3000"` (`app.py` at `2e79844^`, lines 39 and 161–166) | Both loopback origins allowed; `KAZIFORCE_CORS_ORIGIN` accepts a list: **`2e79844`**. Retested through the browser journeys since (`docs/evidence/e2e_browsers.txt`). |
| H-2 | Signed in as a seeded demo worker (2026-11-05) | Demo workers can sign in, and their number displays correctly | They could not sign in, and their number displayed wrongly. The demo seed passed 9-digit numbers straight to the account store, which looks numbers up in normalised `254…` form | The seed normalises numbers and restores the demo workers' consent: **`462c502`**. The same commit fixed a flaky trade-list test (a consenting worker's card carries one extra field). |
| H-3 | Stored keyword-baseline rankings in `match_score` (2026-10-18) | Composite scores fit the column | They did not fit. BM25 scores are unbounded, and `composite_score` was `NUMERIC(6, 5)` (at most 9.99999) in migration 0001 | Migration 0002 widened it to `NUMERIC(12, 5)`: **`458326d`**. The schema before and after is in history. The failing insert itself was not recorded. |
| H-4 | Continuous integration on the first web-interface PR (2026-10-20) | `npm ci` installs from the lock file on a clean runner | Three failures: run **39430972969** `npm error code ERESOLVE` (`@types/node` 20 against vitest's requirement); runs **39471636258** and **39472266811** `npm error code EUSAGE … package.json and package-lock.json … are in sync` (inconsistent lock file; npm 10 on Node 22 against npm 11) | `@types/node` aligned: **`c5f549e`**. Lock file regenerated: **`52b95c3`**. CI moved to Node 24: **`3981c33`**. CI green from run **39472627954**. These were caught by CI, not by local `npm install`. |
| H-5 | Traceability check of Chapter 4 against the system (2026-10-26) | FR-11, NFR-01 and IR-06 met | All three **Partly** (`docs/traceability.md` at `11fefca`): rankings were not persisted (FR-11); only engine time was measured, not request-to-display (NFR-01); no timeouts on model inference or the database (IR-06) | Rankings persisted, NFR-01 measured in Chromium and WebKit, connection and statement timeouts plus an encode budget added: **`33df7f5`**. All three **Done** in `docs/traceability.md` at **`76721f4`**. NFR-01 result: `docs/evidence/nfr01_browser_timing.md`. (S-1 above is a defect in the FR-11 fix.) |

## Defects found during development, before commit

These were found and fixed before the affected code was first committed, so the repository holds the fix and its test but never the failing state. They are **not** regressions.

| # | Test performed | Expected | Actual | Corrective action |
|---|---|---|---|---|
| P-1 | Signed up, then inspected the page after the account was created (2026-10-25) | No PIN remains anywhere in the page | Found during development: the PIN was still held in the page after sign-up | Cleared, and guarded by the e2e test "no PIN is left behind in the page after signing up", committed with the screens: **`928a55a`** / **`1cc2ca8`**. Passing in Chromium and WebKit (`docs/evidence/e2e_browsers.txt`, rows 8 and 18). |
| P-2 | While adding the IR-06 inference time budget, considered encoding job texts in batches so the deadline could be checked between batches (2026-10-29) | Batching leaves the embeddings unchanged | Found during development: encoding in two calls instead of one changes the embeddings by about 1e-7, because sentence-transformers sorts by length to minimise padding. That is enough to reorder near-ties and break reproducibility against the recorded runs | Batching was not adopted. The encode call is left whole and the time budget bounds the wait instead. Documented in `apps/api/src/kaziforce_api/matching/semantic.py` and measured in `tests/test_semantic_scorer.py`: **`33df7f5`**. |
