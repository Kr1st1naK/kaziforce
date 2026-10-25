# Limitations

> **DRAFT for the author to edit (2026-10-18).** Every limitation points to the file or result that
> shows it. Figures refer to the development-split run `results/dev/20261017-132422_6698b8a/`
> (summary: `docs/evidence/dev_results.md`).

## 1. Data

1. **Synthetic profiles only.** All 528 worker profiles and the 80 relevant postings come from the
   generator (`apps/api/src/kaziforce_api/data/synthetic.py`). No real Kenyan worker or client data
   was available (the industry partner supplied requirements documentation only). The results show
   how the system behaves on profiles built to a known specification, not how it performs on real
   users.
2. **The distractor postings are easy to separate.** The 200 non-relevant postings are cleaned US
   white-collar adverts from the Job Skill Set (Mutlu, 2024). Place names, KES amounts and trade
   vocabulary separate them from the Kenyan informal-trade postings, so any configuration can tell
   the two apart. A random ranking within the 80 synthetic postings already reaches MRR 0.260, against
   0.106 for all 280 (`docs/evidence/dev_results.md`, caveat 1).
3. **Rates and budgets are illustrative.** Daily rates and budgets are drawn from per-area KES
   ranges (`RATE_RANGE_KES` in `synthetic.py`), not from market data. Location, availability and
   rate are drawn independently of everything else.
4. **Unequal areas.** Electrician and Tailor have 30 base profiles each, against 12 for the other
   areas, and they supply all held_out profiles. Averages over "all" variants weight those two trades
   more heavily.
5. **The cold-start variant is confounded with the known alias.** `minimal` profiles always use an
   alias that is in the knowledge graph, and they drop availability and rate. There is no minimal
   profile with a withheld alias or with formal wording, so "cold start" here means "sparse profile
   using a known term".

## 2. Vocabulary

6. **Ten occupational areas, 16 accepted aliases.** Fourteen aliases are in the knowledge graph and
   two are withheld. 25 reviewed candidates remain pending (`data/vocabulary/aliases.csv`), and
   including any of them would require regenerating the frozen dataset, which also changes its
   checksums and every result built on it.
7. **Lexical, not usage, validation.** Aliases were checked against dictionaries (kaikki.org
   Wiktionary extract, Swahili Wiktionary) and reviewed by the author. There was no independent
   speaker validation and no usage survey. Dictionary presence shows a term is valid Swahili, not
   that Kenyan workers use it (`data/vocabulary/README.md`). Usage evidence was gathered only for the
   withheld candidates, and for *mshonaji* it is thin (`docs/vocabulary-report.md` §7).
8. **No Sheng, and limited code-switching.** The vocabulary covers Swahili trade names only.
   Code-switched text appears only through the generator's templates.

## 3. Knowledge graph and enrichment

9. **ESCO subset and version.** The graph holds the 11 selected ESCO occupations and their 379
   skills (`data/kg/`). Skills of other trades are invisible to it. The ESCO version used for the
   2026-09-30 download was not recorded. The download date is the reference, and one skill-group
   label came from the pinned API version v1.2.1 because the default version returned an error
   (`data/kg/README.md`).
10. **Exact matching only.** Informal terms and ESCO labels are matched as whole normalised tokens.
    A listed skill that is not an exact ESCO label (e.g. "electrical wiring" rather than "electrical
    wiring plans") is kept as literal text and gains nothing from the graph.
11. **Barber and hairdresser form one area.** Both ESCO occupations belong to area 12, and relevance
    treats them as interchangeable.
12. **The skill hierarchy is not used in scoring.** `TYPE_OF` edges to skill groups are in the graph,
    but enrichment and scoring use only occupation-to-skill edges.

## 4. Matching

13. **Formal availability categories.** The availability criterion uses formal employment categories
    (Full-time, Part-time, Weekends). It does not capture the task-based pattern typical of informal
    trades, where a worker may do several jobs in one day. A Full-time worker is treated as available
    for any job (`docs/scoring-policy.md` §1).
14. **Location ignores travel time.** Sub-areas of the same town score 0.5 ("Nairobi - Kasarani" and
    "Nairobi - Embakasi"), whatever the real travel time between them; different towns score 0.
15. **A priori weights, untested.** The rule weights (0.4/0.2/0.2/0.2) and the hybrid weights
    (α = β = 0.5) were set from domain reasoning and deliberately not tuned against the labels. Their
    effect on real matches is untested.
16. **English-trained semantic model.** all-MiniLM-L6-v2 is trained on English. It has limited
    ability to represent Swahili or code-switched text, which is why it cannot recover the withheld
    aliases (§5, item 19).
17. **Long postings are truncated.** The model reads at most 256 word pieces. 172 of the 200
    distractor descriptions are longer and are embedded from their beginning only. The synthetic
    postings are short.
18. **Startup cost.** Embeddings are cached in memory only, so each process re-encodes the postings
    at startup (about 20–30 s on the development machine). Per-query time after startup is under
    0.2 s (`docs/evidence/dev_results.md`). Persisting embeddings is backlog issue #45.

## 5. Evaluation

19. **Outside its vocabulary, the system falls to the synthetic-only chance level.** On held_out
    profiles every configuration scores MRR 0.22–0.36, around the 0.260 expected from a random ranking
    of the 80 synthetic postings, and the knowledge graph adds +0.000. Without a known term, the
    system finds informal-trade postings but not the right trade.
20. **Gains on known_alias and minimal are expected by construction.** The data generator, the
    relevance labels and the knowledge graph all derive from the same ESCO taxonomy. Postings list
    their occupation's essential ESCO skills, relevance is "same occupational area", and an included
    alias maps to that occupation's ESCO skills. Once enrichment maps the alias, skill overlap
    identifies the area almost exactly (rule_kg MRR 1.000 on both). This shows the mapping works end
    to end; it is not evidence about real postings.
21. **Relevance is occupational only.** A posting is relevant if and only if it is in the worker's
    area. Location, budget and availability do not affect relevance, so the rule criteria for them
    cannot raise the metrics; they can only reorder postings within an area, or demote a relevant one.
22. **One seeded run, no significance testing.** Each configuration was evaluated once
    (tie-break seed 42), with no confidence intervals. Small differences, e.g. full vs rule_kg MRR
    0.918 vs 0.924, are observations, not findings.
23. **Development split only so far.** Baseline results are on the 216 development queries. The
    validation split is unused, and the test split is reserved for the final evaluation.
24. **Small held-out sample.** The withheld-term condition has 24 development queries, from two
    areas.

## 7. Authentication

28. **The sign-in is a proof of concept, not a security control.** Accounts are a phone number
    and a 4-digit PIN, with the role (worker or client) stored on the account.

    **What it does.** The PIN is stored only as a PBKDF2-HMAC-SHA256 hash with a per-account
    salt and 600,000 iterations; the PIN itself is never stored, logged or returned. Sessions
    are server-side, and the cookie value is stored only as a SHA-256 hash, so a copy of the
    database does not hand over usable sessions. The cookie is HttpOnly and SameSite=Lax. An
    account locks for fifteen minutes after five wrong PINs. An unknown number and a wrong PIN
    produce the same response, so the API does not reveal which numbers are registered.

    **What it does not protect against.** A 4-digit PIN has 10,000 combinations, so anyone
    holding a copy of the database can recover PINs by brute force whatever hashing is used;
    the iteration count raises the cost but does not change that conclusion. There is no SMS
    verification, so a number can be registered by someone who does not hold it. There is no
    HTTPS in the local deployment, so the PIN and the session cookie cross the network in
    clear. There is no CSRF token; SameSite=Lax is the only protection. There is no PIN
    change, no account recovery, no revocation of sessions on other devices, and no per-IP
    rate limiting. It demonstrates role-based routing and ownership of profiles and postings;
    it is not a deployable authentication system.

29. **Clients have an account, not a profile.** A client account owns postings and nothing
    else, so there is no client profile screen and the client navigation offers only "Post a
    job" and "My postings".

30. **A phone number is personal data, and the accounts table holds one.** DR-07 is about the
    matching data, and it still holds: a worker profile has no name, no contact detail and no
    identifier beyond a generated UUID, and the synthetic dataset contains none either. Sign-in
    changes the picture at the edge of the system, because an account is keyed by a real phone
    number. That number is never shown to another user, never appears in a recommendation, an
    explanation or the trade list on the confirmation screen, and is returned by the API only to
    the account that owns it. It is stored in clear, however, not hashed, because it is the
    lookup key for signing in. A deployment would need a lawful basis for holding it, a retention
    period and a deletion route; this project has none of those.

## 8. System

31. **The application and the evaluation read different sources, by design.** The interface and
    the API read PostgreSQL; the evaluation reads the frozen CSV files and never calls the API
    (requirement IR-07). This keeps reported results traceable to the recorded dataset
    checksums, and is demonstrated in `docs/evidence/evaluation_isolation.md`, where the
    evaluation was re-run after the interface work with every metric unchanged. The cost is
    that the two paths can drift; `tests/test_store.py` guards against this by checking that
    every profile read back from the database equals its CSV record field for field.
32. **The explanation generator is not yet a backend component.** The explanation shown to a
    worker is composed by the interface from the matched skills, their provenance and the
    per-criterion scores the API returns. Chapter 4 specifies a backend `ExplanationGenerator`
    producing structured output, and `explainability/explain.py` is still a stub, so FR-09 is
    partly met and NFR-02 (explanation coverage) cannot yet be computed. See
    `docs/traceability.md`.
33. **One development machine, two dependency stacks.** Development and timing use an 8 GB Intel
    MacBook (CPU only), which installs an older but compatible torch and NumPy stack. CI runs on
    Linux with the current pins (`requirements.txt`), so embedding values can differ slightly between
    the two.
