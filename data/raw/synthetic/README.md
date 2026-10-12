# Synthetic data (fallback source)

Status: **version 2, seed 42**: 156 base worker groups (528 worker rows) and
280 job postings (80 synthetic, 200 Job Skill Set distractors) for the 10
shortlisted informal-trade areas. Built from the frozen vocabulary
(`data/vocabulary/aliases.csv`, accepted rows only; `area_esco_map.csv`,
selected occupations). No real personal identifiers (DR-07).

Used to simulate cold-start and informal-terminology scenarios and to supply
evaluation data (DR-05; sprint plan S2-6 to S2-8).

## Files

| File | Contents | Holds labels? |
|---|---|---|
| `workers.csv` | `worker_id`, `group_id`, `variant`, `biography`, `skills` (JSON list), `location`, `availability`, `rate_expectation` | No |
| `jobs.csv` | `posting_id`, `title`, `description`, `required_skills` (JSON list), `location`, `availability`, `budget`, `source` (`synthetic` or `job_skill_set`) | No |
| `splits.csv` | `group_id` → `development` / `validation` / `test` | Split only |
| `ground_truth/worker_truth.csv` | per worker row: group, variant, split, area, ESCO occupation, ISCO code, alias used | **Yes** |
| `ground_truth/job_truth.csv` | per job: source, area, ESCO occupation, ISCO code (blank for distractors) | **Yes** |
| `ground_truth/compatibility_matrix.csv` | worker area × job area → `relevant` (0/1). **Editable**; regeneration reads it rather than overwriting it | **Yes** |
| `ground_truth/relevance.csv` | relevant (`worker_id`, `posting_id`) pairs; every other pair is not relevant | **Yes** |
| `inputs/area_skill_pools.csv` | essential/optional ESCO skills of each selected occupation (input, built from the ESCO subset) | — |
| `manifest.json` | seed, parameters, counts per area/split/variant, template counts, sha256 of the inputs | — |
| `difficulty_report.md` | skill overlap between areas and a keyword-overlap baseline (report only) | — |

Scorers must read only `workers.csv` and `jobs.csv`, and must ignore `group_id`
and `variant` (bookkeeping for the split and the core experiment). Area,
occupation, ISCO and ESCO fields exist only under `ground_truth/`.
Direction: **workers are queries and jobs are ranked**. Jobs are one shared
candidate pool, not split.

## How it is built

`apps/api/src/kaziforce_api/data/synthetic.py`, in this order:

1. **Base workers.** By default 12 per area, and 30 for Electrician and Tailor (the
   areas with a held-out alias). Each base worker is a group with:
   - a base occupation (area 12 alternates barber and hairdresser);
   - 4–6 skills sampled from that occupation's ESCO essential skills, plus 0–2
     optional or shared skills ("shared" means also in another shortlisted
     area's pool);
   - a location (20 Kenyan places), availability, daily rate (KES) and
     1–20 years' experience.
2. **Split before variants.** Groups are split 40/20/40 into
   development/validation/test, stratified by area, and `splits.csv` is
   written before any text variant exists. A 12-group area splits 5/2/5
   (largest remainder); a 30-group area splits 12/6/12.
3. **Variants.** Every variant keeps its `group_id`.

   | Variant | Biography | `skills` column | Notes |
   |---|---|---|---|
   | `formal` | Formal English (8 templates): occupation title, skills, location, availability, rate | ESCO skill labels | |
   | `known_alias` | Informal Swahili or code-switched (10 templates) with one accepted `kg_included=yes` alias; no formal skill or occupation labels | The alias only | |
   | `held_out` | Same template and slot values as `known_alias`; only the alias differs | The held-out alias | Electrician (fundi wa stima) and Tailor (mshonaji) only |
   | `minimal` | Known alias plus location (10 templates) | The alias only | Availability and rate blank (cold start) |

4. **Jobs.** 8 per area, in formal English (4 description templates; 6 task
   titles per occupation), with 3–5 ESCO essential skills, location,
   availability and budget. 200 Job Skill Set postings are added as
   distractors, cleaned with `clean_profile_text()`. They are never relevant.
5. **Labels.** `relevance.csv` comes from `compatibility_matrix.csv`. The
   default is relevant iff same area; hairdresser and barber are both area 12,
   so they count as one area. Labels never come from any scorer.

Each stage has its own seeded random stream, so editing templates cannot
change base profiles or the split. Text uniqueness is enforced; there are no
duplicate biographies.

## Regenerate

    python scripts/build_synthetic_dataset.py                 # seed 42, defaults above
    python scripts/build_synthetic_dataset.py --rebuild-pools # also rebuild inputs/ from data/raw/esco/
    python scripts/report_synthetic_difficulty.py             # refresh difficulty_report.md

Optional flags: `--seed`, `--workers-per-area`, `--override AREA_ID=N`,
`--jobs-per-area` and `--distractors`. Distractors need
`data/raw/job_skill_set/all_job_post.csv`; without it they are skipped, and the
manifest records that.

In code, `load_synthetic_data()` returns the profile files and
`load_synthetic_ground_truth()` returns the labels (both in
`kaziforce_api.data.loaders`).

**The files are committed and frozen.** The test split must not change after
Sprint 2. `manifest.json` records the sha256 of both vocabulary files, and
`tests/test_synthetic_dataset.py` fails if the vocabulary changes without a
regeneration.

## Tests

- **`tests/test_synthetic_dataset.py`** (on these files):
  - no group spans two splits;
  - profile files have no label or occupation columns;
  - held-out aliases appear only in `held_out` variants of Electrician and Tailor, and never
    in the KG vocabulary;
  - informal variants contain no formal skill or occupation labels;
  - no duplicate biographies;
  - counts and checksums match the manifest;
  - relevance follows the matrix;
  - distractors contain no contact details.
- **`tests/test_synthetic.py`** (the generator, on committed inputs):
  - parameters are respected;
  - the same seed gives identical files;
  - splits are written before variants;
  - edits to the matrix are respected.

## Difficulty (see `difficulty_report.md`)

- **Skill overlap:** 29 of 45 area pairs share at least one ESCO skill. The
  construction trades overlap most (carpenter–bricklayer Jaccard 0.39); the
  median is 0.01.
- **Keyword baseline:** shared content words alone rank a relevant job first
  for development workers as follows.

  | Variant | Synthetic jobs only | With distractors |
  |---|---|---|
  | `formal` | **97%** (77% with no tie) | 81% |
  | informal (`known_alias`, `held_out`, `minimal`) | 13–16% | 12–15% |

  - **`formal` is close to 100%:** it is easy by design, because its biography repeats the
    occupation title and ESCO labels that the jobs use.
  - **Informal variants score about chance:** each area holds 10% of the synthetic jobs. Their
    only shared words are place names and availability.

## Job Skill Set cleaning: before and after (`clean_profile_text`)

These are the first 150 characters of five raw descriptions, chosen with no
contact details in the excerpt. Across all 1,167 descriptions, cleaning leaves
no emails, @handles, URLs or phone numbers.

| job_id | Before | After |
|---|---|---|
| 3901661179 | `HEALTHCARE EXPERIENCE REQUIRED\nJOB SUMMARY THE CHIEF HUMAN RESOURCES OFFICER IS DIRECTLY RESPONSIBLE FOR OVERSEEING HR TASKS AND HR SYSTEMS, HANDLING ` | `healthcare experience required job summary the chief human resources officer is directly responsible for overseeing hr tasks and hr systems, handling ` |
| 3904726452 | `DESCRIPTION\n\nABOUT NEIGHBORWORKS AMERICA\n\nHAVE YOU EVER WORKED FOR AN ORGANIZATION WHERE THE TOTAL REWARDS PACKAGE INCLUDED A 401(K) MATCH UP TO 12%? ` | `description about neighborworks america have you ever worked for an organization where the total rewards package included a 401(k) match up to 12%? do` |
| 3899531088 | `IT OPERATIONS MANAGERNASHVILLE, TN UP TO $80K\nBELL & ASSOCIATES HAS BEEN ENGAGED TO SEARCH FOR AN IT OPERATIONS MANAGER FOR OUR CLIENT! THIS ROLE IS O` | `it operations managernashville, tn up to $80k bell & associates has been engaged to search for an it operations manager for our client! this role is o` |
| 3902954343 | `JOB TITLE: DOCUMENT REVIEW SPECIALISTDURATION: 09- MONTHS CONTRACT (GOOD POSSIBLE EXTENSIONS)LOCATION: ONSITE ROLE- NEW YORK, NY 10036PAY RATE: $55.00` | `job title: document review specialistduration: 09- months contract (good possible extensions)location: onsite role- new york, ny 10036pay rate: $55.00` |
| 3901981049 | `POSITION SUMMARY:\nTHE HUMAN RESOURCES BUSINESS PARTNER III IS A STRATEGIC CONSULTING RESOURCE TO EXECUTIVE LEADERSHIP WITHIN THE INTERNATIONAL BUSINES` | `position summary: the human resources business partner iii is a strategic consulting resource to executive leadership within the international busines` |

## Notes

- **fundi seremala** (pending) is not used.
- **Job category:** the database schema has `job_posting.category`. The synthetic `jobs.csv`
  leaves it out, because filling it with the area would expose the label. Keep it empty
  (or use `title`) when loading into PostgreSQL (S2-11).
- **Superseded version:** version 1 (12 workers, 12 jobs, 8 hand-written occupation specs) is
  replaced by this version.
