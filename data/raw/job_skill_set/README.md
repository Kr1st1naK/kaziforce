# Job Skill Set (supplementary job-side corpus)

| | |
|---|---|
| Citation | Mutlu, B. (2024). *Job-skill-set* (Version 2) [Data set]. Kaggle. https://doi.org/10.34740/KAGGLE/DSV/10201355 |
| Source page | https://www.kaggle.com/datasets/batuhanmutlu/job-skill-set/versions/2 |
| License | CC BY-SA 4.0 (attribution required; derivatives must be shared under the same license) |
| File | `all_job_post.csv` — 4,905,506 bytes, 1,167 postings (not committed; see `data/README.md`) |
| SHA-256 | `2ae32298328bbfc1f36a1bdeea9fddee1a566a3022a256f9d24fa57d177a168e` |
| Columns | `job_id`, `category`, `job_title`, `job_description`, `job_skill_set` |

**How to obtain:** download `all_job_post.csv` manually from the source page
(requires a Kaggle account) and place it in this folder. Verify with
`shasum -a 256 all_job_post.csv`.

**Coverage caveat:** every posting falls in one of five formal white-collar
categories (INFORMATION-TECHNOLOGY, BUSINESS-DEVELOPMENT, FINANCE, SALES, HR).
It contains no informal-trade postings, so it can only support job-side
pipeline development and proof-of-concept evaluation, not informal-trade
matching itself (proposal Sections 1.7 and 3.2.1).

Loaded by `apps/api/src/kaziforce_api/data/loaders.py::load_job_corpus`.
