# Knowledge graph inputs (ESCO subset)

The ESCO data the knowledge graph is built from. It is committed so the graph
can be rebuilt from a fresh clone and in CI without the gitignored
`data/raw/esco/` download. Built by `scripts/build_kg_inputs.py`; the
manifest records sources, dates, counts and sha256 values, and
`tests/test_kg_inputs.py` fails if the files drift from it.

| File | Rows | Contents |
|---|---|---|
| `occupations.csv` | 11 | The ESCO occupations selected for the 10 shortlisted areas: URI, label, ESCO code |
| `occupation_broader.csv` | 1 | barber → hairdresser (nearest selected occupation by ESCO code prefix) |
| `skills.csv` | 379 | Their essential and optional skills: URI, label, type (305 skill, 74 knowledge), reuse level |
| `occupation_skills.csv` | 507 | Occupation → skill, `essential` (234) or `optional` (273) |
| `skill_broader.csv` | 379 | Skill → broader concept (one hop of the ESCO hierarchy) |
| `skill_groups.csv` | 140 | Broader concepts: 114 ESCO skill groups, 26 ISCED-F knowledge fields |
| `manifest.json` | — | Sources, dates, counts, input and output sha256 |

**No area columns.** The occupational area is the evaluation label space, so it
never reaches the graph. The withheld aliases are not here either: aliases come
from `data/vocabulary/aliases.csv` through `kaziforce_kg.vocabulary`.

**Broader-concept labels.** The ESCO subset download (2026-09-30) does not
include the broader concepts, so their English labels were fetched once from
the ESCO API (`resource/concept`) on 2026-10-12. The API's default version
returns HTTP 500 for one skill group (S1.5.3, "More than one value found for
field 'hasSkillType'"); that label was taken from the pinned version v1.2.1
(`label_source` column). For the groups checked, labels were identical across
the default version and v1.1.2, v1.2.0 and v1.2.1.

**ESCO version.** The subset download did not record an ESCO version (the API
default at the time was used); the download date is the reference.

Rebuild (offline; reuses the committed labels):

    python scripts/build_kg_inputs.py              # needs data/raw/esco/ (scripts/download_esco.py)
    python scripts/build_kg_inputs.py --refetch    # also re-fetches the 140 labels from the ESCO API

ESCO classification © European Union, reused with attribution under the
European Commission reuse policy (Decision 2011/833/EU).
