# Scoring policy (decided before any score exists)

**Decided and committed 2026-10-16, before any scorer was implemented or any
score computed** (keyword score revised to BM25 on 2026-10-17, still before any score; see "Revisions" below). These rules are frozen. Any change after results exist is
recorded below under "Deviations" with its date and reason, and the affected
results are re-run and labelled as such.

Every scorer receives an enriched worker and an enriched job: the profile plus
the `Enrichment` produced by the configuration's enricher (`ProfileEnricher`
with the knowledge graph, `NullEnricher` without). Scorers never look at which
enricher was used, nor at dataset bookkeeping (group, variant, split) or labels.

## 1. Rule-based score

Four criteria, each scored in [0, 1].

| Criterion | Score | Present when |
|---|---|---|
| `skill_overlap` | \|W ∩ J\| / \|J\| | both W and J are non-empty |
| `location` | 1 if the locations are equal; 0.5 if the same town; otherwise 0 | both locations given |
| `budget_fit` | 1 if rate ≤ budget; otherwise max(0, 1 − (rate − budget) / budget) | both rate and budget given, budget > 0 |
| `availability` | 1 if equal, or if the worker is Full-time; otherwise 0 | both availabilities given |

- **Skill sets.**
  - W is every skill the worker's enrichment holds: stated (listed, or literal text) and inferred.
  - J is the job's **stated** requirements only, as the posting lists them.
  - Skills a job's text might imply are ignored, so enrichment cannot inflate a job's requirements.
  - Skill identifiers are compared as opaque strings: ESCO URIs, or `text:<normalised entry>`.
- **Location.**
  - Values are compared after trimming and case-folding.
  - "Same town" means the part before `" - "` is equal, e.g. "Nairobi - Kasarani" and "Nairobi - Embakasi".
- **Availability.** A Full-time worker can take any job; otherwise the values must match exactly.
- **Default weights:** skill_overlap 0.4, location 0.2, budget_fit 0.2, availability 0.2.
  - They are assigned a priori from domain reasoning: skills dominate, and the three practical constraints count equally.
  - They are **not** tuned against the evaluation labels. The reference labels are occupational (same area) and ignore location, budget and availability, so tuning against them would drive those weights to zero as an artefact of the labelling rather than as a finding.

### Missing-field rule (renormalisation)

A criterion is scored only when the field is present on **both** sides. Absent
criteria are dropped, and the weights of the present criteria are renormalised
to sum to 1:

    rule = Σ_present w_c · s_c  /  Σ_present w_c        (rule = 0 if no criterion is present)

Missing information therefore neither adds nor subtracts score by itself. In this dataset:

- the 200 Job Skill Set distractor postings have no location, budget or availability, so they are scored on `skill_overlap` alone;
- `minimal` worker profiles have no availability or rate, so they are scored on `skill_overlap` and `location`.

The alternative, scoring a missing field as 0, would systematically penalise the distractors. They are never relevant, so the system would gain an advantage that correlates with the labels without any matching ability. Scoring missing fields as a neutral 0.5 would add the same constant to unrelated postings.

The per-criterion breakdown reports an absent criterion as absent, not as 0.

## 2. Keyword baseline

No knowledge graph and no embeddings. The worker text is the biography plus
the listed skills; the job text is the title, the description and the listed
required skills.

- **Tokeniser** (frozen):
  1. Unicode NFKC, then lower-case.
  2. Tokens are maximal runs of the letters a–z.
  3. Keep tokens of 3 or more letters.
  4. Remove the function words listed below.
- **Score:** Okapi BM25, with the worker text as the query and each posting as a document:

      BM25(q, d) = Σ_{t ∈ q} IDF(t) · tf(t, d) · (k1 + 1) / (tf(t, d) + k1 · (1 − b + b · |d| / avgdl))
      IDF(t) = ln(1 + (N − n(t) + 0.5) / (n(t) + 0.5))

  - Each distinct query term counts once.
  - N, n(t), |d| and avgdl come from the candidate pool being ranked (the 280 postings); no labels are involved.
  - k1 = 1.2 and b = 0.75 are the standard defaults, not tuned.
  - This IDF form is never negative.

**Why this tokeniser.** The stop-word list contains **closed-class function
words only**: articles, pronouns, possessives, demonstratives, prepositions,
conjunctions, auxiliaries and copulas, in English and Swahili. It was written
from those grammatical categories, not from the data. **Content words are kept
even when the generated templates use them often**, e.g. *kazi*, *miaka*,
*uzoefu*, *experience*, *available*, *years*, *rate*, *day*, *ksh*, *kes*. A
keyword matcher deployed on real profiles would not know which content words a
data generator happened to repeat.

The old difficulty-report script (`scripts/report_synthetic_difficulty.py`)
removed several such content words. Its list is **not** reused here; that
script and its committed report are a dataset check and stay as they are. Some
function words do occur in the templates (*mimi*, *niko*, *hapa*), which is
unavoidable for function words, and they are on the list because of their
grammatical category. One- and two-letter words (*na*, *ni*, *wa*, *ya*, *is*,
*in*, *at*, …) are removed by the length rule.

**Why BM25.** It is the standard lexical baseline in retrieval and in the job-matching literature cited in Chapter 2, so the comparison is directly interpretable. Its length normalisation (b) also stops the long Job Skill Set descriptions (about 3,300 characters) from outranking short postings by length alone. Its parameters are fixed defaults and nothing is fitted to the data.

English function words:

    about above after again against all also although among and any are because been before being below
    between both but can cannot could did does doing down during each either few for from further had has
    have having her here hers herself him himself his how into its itself may might more most must myself
    neither nor not off once only other ought our ours ourselves out over own per same shall she should some
    such than that the their theirs them themselves then there these they this those through too under until
    upon very via was were what when where which while who whom whose why will with within without would yet
    you your yours yourself yourselves

Swahili function words:

    mimi wewe yeye sisi nyinyi ninyi wao yangu yako yake yetu yenu wangu wake wetu wenu zangu zako zake
    huyu huyo yule hawa hao wale hii hiyo ile hizi hizo zile kwa katika kwenye kutoka hadi pia lakini ama
    kama ili bila tena sana niko uko yuko tuko mko nina una ana tuna mna ndiyo siyo hapa pale huko

## 3. Semantic score

- **Model and text.** all-MiniLM-L6-v2 sentence embeddings, L2-normalised.
  - The worker text is the biography, followed by the labels of the skills in the worker's enrichment.
  - The job text is the description.
  - The same rule applies in every configuration; only the enrichment's contents differ.
- **Score:** cosine similarity, clipped to [0, 1] (negative similarity is treated as no similarity).
- **Caching:** embeddings are cached in memory by text, and no database is used.

## 4. Hybrid score

    composite = α · rule + β · semantic,   α = β = 0.5

α and β are assigned a priori and are not tuned against the labels, for the
reason given in §1.

## 5. Ranking and ties

Jobs are ranked by descending score. Ties are broken by one fixed random order
of the 280 postings (seed 42), the same order for every configuration, so no
configuration gains from the incidental order of `jobs.csv`.

## Revisions before any score existed

| Date | Change | Reason |
|---|---|---|
| 2026-10-17 | Keyword score changed from Jaccard similarity to Okapi BM25 (k1 = 1.2, b = 0.75); tokeniser unchanged | Comparability with the BM25 baselines in the literature cited in Chapter 2. No scorer had been run on the dataset. |

## Deviations

None.
