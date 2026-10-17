# Documentation

| Document | What it is |
|---|---|
| [`scoring-policy.md`](scoring-policy.md) | How every configuration scores and ranks, fixed before any score existed: rule-based criteria, weights, the missing-field rule, the BM25 keyword baseline, semantic and hybrid scores, tie-breaking |
| [`evidence/`](evidence/) | Generated evidence for the thesis, each file stamped with the commit that produced it |
| [`evidence/kg_stats.md`](evidence/kg_stats.md) | Knowledge graph node and edge counts by type, schema, occupations, withheld-alias check |
| [`evidence/enrichment_example.md`](evidence/enrichment_example.md) | Worked enrichment example (one profile before and after, every inferred skill with its graph path) and the occupation-mapping check over the development split |
| [`evidence/dev_results.md`](evidence/dev_results.md) | Development-split baseline: seven configurations, P@3/5/10 and MRR by variant, knowledge-graph effect, response time, and how to read them |
| [`evidence/demo_run.txt`](evidence/demo_run.txt) | Transcript of the end-to-end command-line demo (one worker, top 10) |
| [`test-results.xml`](test-results.xml) | JUnit record of the latest full test run |
| [`vocabulary-report.md`](vocabulary-report.md) | How the informal-term vocabulary was checked: dictionary evidence, ESCO mapping, shortlist, decisions (pre-decision snapshot, see its status note) |
| [`vocabulary-review-sheet.md`](vocabulary-review-sheet.md) | One line per candidate alias, as reviewed (pre-decision snapshot) |
| [`wireframes/`](wireframes/) | Low-fidelity wireframes of the four screens: worker profile, job posting, ranked matches, explanation |
| [`sprint-plan.md`](sprint-plan.md) | The original six-sprint plan (partly superseded by the three-sprint structure; see its status note) |
| [`ToDo.md`](ToDo.md) | Early phase checklist from project start (historical) |

Data documentation lives next to the data: [`../data/README.md`](../data/README.md),
[`../data/kg/README.md`](../data/kg/README.md) and
[`../data/raw/synthetic/README.md`](../data/raw/synthetic/README.md).
