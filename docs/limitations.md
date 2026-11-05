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
22. **One run, because the system is deterministic — not because variance went unmeasured.**
    Nothing is trained and nothing is sampled at inference, so repeated runs on the same commit
    and the same frozen dataset produce identical metrics. Two full development runs on one
    commit were compared and differed in no reported value: 0 of 35 aggregate rows and 0 of
    1,512 per-query rows; the composite scores are identical bit for bit. Only wall-clock
    timings differ. Confidence intervals over repeated runs would all have zero width.
    `docs/evidence/determinism.md` has the comparison. Three things this does **not** claim:
    it says nothing about **other datasets**, only one was used; it does not establish
    **significance between configurations**, so a small difference such as full vs rule_kg MRR
    0.918 vs 0.924 remains an observation on one dataset, and a paired test over the 216
    per-query observations is the right tool if such a claim is to be made; and it is a claim
    about **this machine**, since floating-point results could differ in their last bits on
    other hardware.
23. **Development split only so far.** Baseline results are on the 216 development queries. The
    validation split is unused, and the test split is reserved for the final evaluation.
24. **Small held-out sample.** The withheld-term condition has 24 development queries, from two
    areas.

25. **Explanation coverage fails exactly where the vocabulary does.** Under the definition fixed
    in `docs/scoring-policy.md` §7, the full system can state a concrete, checkable reason for
    79.2% of the top-10 results on the development split, against the 85% that NFR-02 asks for.
    The shortfall is not spread evenly: formal wording reaches 89.2%, a known alias 90.3% and a
    minimal profile 87.8%, while a withheld alias reaches **0.0%**. A worker whose words the
    vocabulary does not know reaches no occupation, so no skill is inferred, so no skill is
    shared, so there is nothing the system can honestly say. The cold-start limitation of item 19
    is therefore also an explainability limitation, and widening the vocabulary — not changing
    the generator — is what would close it.

## 6. Authentication

26. **The sign-in is a proof of concept, not a security control.** Accounts are a phone number
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

27. **Clients have an account, not a profile.** A client account owns postings and nothing
    else, so there is no client profile screen and the client navigation offers only "Post a
    job" and "My postings".

28. **A phone number and a name are personal data, and the accounts table holds them.** DR-07 is
    about the matching data, and it still holds: a worker profile has no name, no contact detail and
    no identifier beyond generated UUIDs, and the synthetic dataset contains none either. The
    account is where personal data lives. An account is keyed by a real phone number, and a worker
    now also gives a first and last name at sign-up.

    **What changed.** Both are encrypted in the application, not just on disk: AES-256-GCM with a
    random nonce per value and a key-version prefix, under a key held in the server's environment.
    The phone number is found at sign-in by an HMAC under a second key, so the table holds no
    plaintext number and a copy of it cannot be searched for one. Names live on the account and
    never on the worker profile, and never reach the embedding, the enrichment or the scoring.
    The mechanism, the four places a value is decrypted and the migration are in
    `docs/privacy-and-keys.md`.

    **Who sees them.** Not other workers, and not matching. A *client* sees a worker's name and
    phone number only if that worker ticked the agreement at sign-up (or later on their profile)
    and has not withdrawn it: unticking it hides the name, the number and the profile link on the
    next request, and the profile endpoint then answers exactly as it does for a worker who does
    not exist. A client is never given a name field and there is no client profile. Anyone, of any
    role, is shown their own number.

    **The privacy implication, for Chapter 6.** This is a deliberate reversal of this item's
    earlier wording, which said the number was never shown to another user. A worker's
    contact details now reach strangers: any client, and a client account needs only an
    unverified phone number to create (item 38). The safeguards are consent, withdrawal,
    a per-account rate limit on profile views (item 38), and that only workers in a trade's
    first-five list can be reached. They reduce the exposure; they do not make it consensual
    in a verified sense. Nothing stops a client keeping a number once seen, and withdrawing
    consent does not recall it. A deployment would need a lawful basis (in Kenya, the Data
    Protection Act, 2019), a retention period, a way for a worker to see who viewed them and
    to delete their account, and a privacy notice. This project has none of those.

    **Existing accounts.** Accounts made before names existed have no name and are not
    consenting, so they appear as anonymous cards and cannot be opened. A worker adds a name and
    ticks the agreement on their profile when they choose. Nothing is shown about them that they
    did not agree to.

## 7. System

29. **The application and the evaluation read different sources, by design.** The interface and
    the API read PostgreSQL; the evaluation reads the frozen CSV files and never calls the API
    (requirement IR-07). This keeps reported results traceable to the recorded dataset
    checksums, and is demonstrated in `docs/evidence/evaluation_isolation.md`, where the
    evaluation was re-run after the interface work with every metric unchanged. The cost is
    that the two paths can drift; `tests/test_store.py` guards against this by checking that
    every profile read back from the database equals its CSV record field for field.
30. **A worker is shown sentences, not numbers.** The explanation screen renders the generated
    sentences and nothing else: no component scores, no criterion table, no raw graph path. The
    sentences are themselves derived from those graph paths and score components, so FR-09 is
    met, but the structured evidence is no longer visible in the interface and therefore not
    capturable as a screenshot. It is recorded instead in
    `docs/evidence/explanation_payload.md`, generated by `scripts/explanation_example.py` from
    the frozen development split. Two consequences for the thesis: the four provenance labels
    ("Listed by you", "Your own words", "Inferred via *fundi wa umeme*", "Inferred via
    occupation: *electrician*") no longer appear on screen, though the provenance itself is
    still stated in words by the vocabulary note; and "Not assessed" is no longer rendered as a
    literal label, because an unassessed criterion is now said in a sentence instead. Whether a
    worker would want the detail on demand is a usability question, and no usability study was
    conducted (NFR-04).

31. **One development machine, two dependency stacks.** Development and timing use an 8 GB Intel
    MacBook (CPU only), which installs an older but compatible torch and NumPy stack. CI runs on
    Linux with the current pins (`requirements.txt`), so embedding values can differ slightly between
    the two.

32. **A client is shown an unordered sample of workers, not matches.** The confirmation screen
    lists a sample of the workers in the posting's trade, with the count. The cards carry no
    score, no rank and no numbering, and are drawn the same whether or not the worker has a name.
    This is deliberate and not an omission. Matching runs from worker to job only: the relevance
    labels (a posting is relevant to a worker if and only if it is in their occupational area,
    item 21) were built for that direction, and there are no labels and no evaluation for ranking
    workers against a posting (Chapter 4 scopes job-to-worker matching out). Any order the page
    imposed would be read as a ranking, whether it was by recency, rate, location or arrival, so
    the only presentation that does not claim something unevaluated is no order at all. The sample
    is the first five matching workers by `worker_id`, a random identifier, so it is arbitrary
    and fixed: the same five appear for every posting in the trade until the pool changes.

    **What the cards now add.** A worker who has a name and has consented is shown with their name,
    as a link to a page with their trade, facts, their own words and a number to ring. That is a
    way to *contact* a worker, not a statement that they *fit* the job, and the design keeps the
    two apart: a named card is no larger, no earlier and no more emphasised than an anonymous
    one; there is no "recommended" and no sort; consenting does not change which workers are in
    the sample or how many there are (a test holds this). It is still true that a client cannot
    see which workers suit their job best. Bidirectional matching, with its own labels and
    evaluation, is future work. The page also gives a client nothing to compare two workers
    by except what each wrote about themselves.

    **The consequence of the sample (item 36).** Because the five are fixed and random, a
    worker who consents is usually not among them, and so usually cannot be reached.

## 8. Privacy and security

33. **`POST /recommend` with a `worker_id` needs no sign-in.** Anyone who has a worker's
    internal identifier can ask for that worker's ranked jobs and gets back their profile (words,
    location, availability, rate). It returns no name and no phone number, and a test holds
    that, and a client is never given the internal identifier (they get a separate `public_id`,
    and only for consenting workers). It remains an open endpoint: it was built for the
    command-line demo and the evaluation, and the project never closed it. It is reachable by
    anyone who can guess or learn a UUID. A deployment should require a signed-in worker and
    their own `worker_id`.

34. **The keys live in the server's environment.** There is no key-management service, no hardware
    module and no automated rotation. Anyone who can read the process environment or the `.env`
    file can read every encrypted value, and the keys sit on the same machine as the database.
    The `v1:` prefix and the multi-key cipher exist so rotation can be added; the script that
    re-encrypts the rows and recomputes the lookup hash does not exist. Losing a key loses the data
    it protects. In development a missing key falls back to a fixed, public one with a warning,
    which protects nothing; only a non-development environment refuses to start without keys.

35. **No disk encryption, and no TLS to the database, on the development machine.** Application-level
    encryption protects a copy of the database, a backup or a query result. It does not protect a
    running server, a memory dump, or the process's own environment. The local PostgreSQL
    reports TLS off, and the data directory is not encrypted at rest. Whole-disk encryption and a
    TLS database connection belong to the host and were not set up.

36. **Contactable workers are rarely visible.** A trade list shows five workers, chosen by a random
    identifier (item 32). A worker who signs up, names themselves and consents is therefore unlikely
    to appear in it: in a trade of fifty, about one chance in ten. The feature works, but for most
    workers it will not be reached. Showing consenting workers first would fix the arithmetic and
    would be an ordering that favours a group, which this project has declined to build
    (item 32). The demo seed (`scripts/seed_demo_workers.py`) gives its three workers identifiers that
    sort ahead of the random ones so a demonstration is reliable; that is a demonstration
    accommodation, and the end-to-end tests rely on it for the same reason.

37. **A 4-digit PIN is weak against anyone holding the database.** Item 26 says so; it is repeated here
    because it limits everything above it. PBKDF2 at 600,000 iterations raises the cost of trying
    each PIN and cannot make 10,000 possibilities a large number: a copy of the table yields every
    PIN in seconds, which signs the attacker in as that person, and a signed-in worker's contact
    details are then theirs to change. A server-side pepper with upgrade-on-login would put a secret
    outside the database; it is proposed and not built (`docs/privacy-and-keys.md`).

38. **Consent and identity are not verified, and the limit on viewing is soft.** There is no SMS
    verification, so a worker account can be created with a number its owner does not hold, with
    a name the person did not choose, and ticked as consenting on their behalf. The name is
    whatever was typed. A client account needs only a number and a PIN, takes seconds to make, and
    is not limited per address, so the rate limit on `GET /workers/<public_id>` (30 views a
    minute per account, counting misses) slows a person using one account and not one making many.
    It is in memory, per process, and forgets on restart. An unknown number is told it already
    has an account when it signs up, so sign-up reveals which numbers are registered (the sign-in
    response does not).

39. **Plain HTTP until deployment.** The PIN, the session cookie, a worker's name and their phone number
    cross the network unencrypted in the local setup. HTTPS has been *prepared for* and not done:
    the API refuses to start in production without a named origin and sends security headers and
    HSTS there, but the list of places that still assume `http://` (the web app's default API
    address, the development CORS origins, the Flask development server, the database URL,
    the end-to-end suite) is in `docs/privacy-and-keys.md`. No claim is made here about how the
    system behaves behind TLS: it has not been run that way.

40. **The access log records who viewed whom.** A profile view is `GET /workers/<public_id>`, so the
    web server's request log ties a client's address to a worker's page. The id is opaque and the log
    is the server's, not the application's, and no retention rule exists for it.
