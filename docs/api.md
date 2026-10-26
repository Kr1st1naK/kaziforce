# REST API

Flask API between the web app and the recommendation engine (IR-02). JSON in, JSON out.
Implementation: `apps/api/src/kaziforce_api/app.py` (routes, validation),
`service.py` (engine, response building), `auth.py` (phone numbers, PINs, session
tokens) and `data/accounts.py` (accounts, sessions, ownership). Tests:
`tests/test_api.py`, `tests/test_api_db.py`, `tests/test_auth.py` and
`tests/test_api_accounts.py`.

| Method | Path | Purpose | Sign-in |
|---|---|---|---|
| GET | `/health` | Readiness and the size of the candidate pool | — |
| POST | `/auth/accounts` | Create an account; signs it in | — |
| POST | `/auth/sessions` | Sign in | — |
| DELETE | `/auth/sessions` | Sign out | — |
| GET | `/auth/session` | Who is signed in, and what they own | Any |
| POST | `/recommend` | Ranked jobs for a stored worker or a typed-in profile | Optional |
| POST | `/workers` | Store a worker profile; returns its identifier and enrichment | Optional |
| GET | `/workers/me` | The signed-in worker's own profile and enrichment | Worker |
| POST | `/jobs` | Store a job posting, add it to the candidate pool, return how it was understood | Optional |
| GET | `/jobs` | The signed-in client's own postings | Client |
| GET | `/jobs/{posting_id}` | How a stored posting was understood | Optional |

"Optional" means the endpoint works signed out, and does more when signed in: a stored
profile or posting is claimed by the account that created it.

Run it:

    flask --app kaziforce_api.app run          # http://127.0.0.1:5000

The engine loads in the background at startup: the knowledge graph, 280 postings, the
all-MiniLM-L6-v2 model and the job embeddings, taking about 20–30 s on CPU. Until it is ready,
`/health` reports `"ready": false` and `/recommend` answers 503. After that, a request takes
well under 0.2 s.

**Profile source.** Stored workers and the job postings are read from PostgreSQL
(`DATABASE_URL`). Set `KAZIFORCE_PROFILE_SOURCE=csv` to read the frozen CSVs instead
(e.g. without a database); profiles cannot then be stored, and `POST /workers` and
`POST /jobs` answer 501. An unseeded database makes startup fail, and `/recommend` then
answers 500.

**The candidate pool grows, the evaluation does not.** A posting stored through
`POST /jobs` joins the live candidate pool at once, so the pool is larger than 280 for the
rest of that server's life, and every posting's tie-break position is recomputed. This is
correct behaviour for a running service, and it never touches the published metrics: the
evaluation runner (`scripts/evaluate.py`) builds its own pipeline from the frozen CSV
dataset and never calls this API, so results always come from exactly the 280 committed
postings. `GET /health` reports the live pool size, so a demo can state it.

Profiles and postings stored during a demo or a browser test stay in the database.
`python scripts/seed_database.py --reset` clears them and re-seeds, leaving exactly the
frozen dataset. Restart the API afterwards, because it holds the candidate pool in memory.

**CORS.** Browser requests are allowed from `http://localhost:3000` and
`http://127.0.0.1:3000` (the Next.js dev server, either spelling).
`KAZIFORCE_CORS_ORIGIN` replaces that list and takes comma-separated origins. Any other
origin gets no CORS headers, so the browser blocks the response. Credentials are allowed
(`Access-Control-Allow-Credentials: true`), because the session travels in a cookie.

**Use one host throughout.** The session cookie is `SameSite=Lax`, so a page served from
`localhost:3000` will not send it to `127.0.0.1:5000`: the browser treats those as
different sites. The web app derives the API host from the page's own hostname for this
reason, and the browser tests pin both to `127.0.0.1`.

**On macOS, use `127.0.0.1:5000`, not `localhost:5000`.** AirPlay Receiver listens on port
5000 over IPv6 and answers 403, while Flask binds IPv4 only, so `localhost` can reach the
wrong service. Turn AirPlay Receiver off in System Settings → General → AirDrop & Handoff,
or keep using `127.0.0.1`.

## Accounts and sessions

A proof-of-concept sign-in so a worker's profile and a client's postings belong to
someone. A person is identified by a Kenyan mobile number and a 4-digit PIN.
`docs/limitations.md` §7 states plainly what this does and does not protect against.

- The PIN is stored as PBKDF2-HMAC-SHA256, 600,000 iterations, with a per-account salt.
  It is never logged and never returned.
- Five wrong PINs lock the account for 15 minutes (423). The counter is committed even
  though the attempt fails, so a lockout cannot be rolled back.
- The session lives server-side in a `session` table, keyed by the SHA-256 of the token.
  The token itself is only ever in an `HttpOnly`, `SameSite=Lax` cookie, which expires
  after 7 days. `Secure` is set when the request arrives over HTTPS.
- Phone numbers are normalised to `254XXXXXXXXX`. `0712345678`, `712345678`,
  `254712345678` and `+254 712 345 678` are the same account. Responses give the local
  form (`0712345678`).

### `POST /auth/accounts`

```json
{ "phone": "0712345678", "pin": "4821", "role": "worker" }
```

| Field | Rules |
|---|---|
| `phone` | Required, a Kenyan mobile number in any of the forms above |
| `pin` | Required, exactly 4 digits |
| `role` | Required, `worker` or `client` |

**Response 201** is the session payload below, and sets the session cookie. A phone
number already registered is a 409 `already_exists`; the role is **not** part of the
identity, so one number cannot hold both a worker and a client account.

### `POST /auth/sessions`

The same body without `role`. **Response 200** is the session payload, and sets the
cookie. A wrong number or PIN is a 401 `invalid_credentials` with the same message
either way, so the response does not reveal whether the number is registered.

### `DELETE /auth/sessions`

Ends the session server-side and clears the cookie. `{ "signed_out": true }`. Safe to
call when not signed in.

### `GET /auth/session`

The session payload for whoever holds the cookie; 401 if nobody does.

```json
{
  "account": { "account_id": "a3f1…", "phone": "0712345678", "role": "worker" },
  "worker_profile_id": "e5a7c1d2-…",
  "postings": 0
}
```

`worker_profile_id` is `null` for a worker who has not created a profile yet, and always
`null` for a client. `postings` counts a client's own postings, and is always 0 for a
worker. Between them the interface knows where to send the person and which navigation
to draw.

**A client has an account, not a profile.** Clients are not matched, so there is nothing
to enrich and no profile screen. See `docs/limitations.md` item 29.

## `GET /health`

```json
{ "status": "ok", "ready": true, "candidate_jobs": 280 }
```

`candidate_jobs` is 0 until the engine is ready, and grows as postings are stored.

## `POST /recommend`

Ranked jobs for one worker, either a **stored** worker (`worker_id`) or a **typed-in** profile
(`worker`). Send exactly one of the two — or neither, when a signed-in worker is asking for
their own matches, in which case their profile is used. A signed-in worker who has no profile
yet gets a 403.

### Request

```json
{
  "worker_id": "3917d39f-d0c0-46c2-aa34-9158711f68f3",
  "k": 10,
  "configuration": "full"
}
```

```json
{
  "worker": {
    "biography": "Niko Nyeri, ni fundi wa umeme.",
    "skills": ["fundi wa umeme"],
    "location": "Nyeri",
    "availability": "Part-time",
    "rate_expectation": 2000
  },
  "k": 10
}
```

| Field | Type | Rules |
|---|---|---|
| `worker_id` | string | A worker stored in PostgreSQL (seeded with the development-split workers by `scripts/seed_database.py`) |
| `worker.biography` | string | Required, non-empty, at most 4000 characters |
| `worker.skills` | string[] | Optional (default `[]`), at most 50 entries of 200 characters; blank entries are dropped |
| `worker.location` | string \| null | Optional, at most 200 characters, e.g. `"Nairobi - Kasarani"` |
| `worker.availability` | `"Full-time"` \| `"Part-time"` \| `"Weekends"` \| null | Optional |
| `worker.rate_expectation` | number \| null | Optional, KES per day, ≥ 0 |
| `k` | integer | 1–50, default 10 |
| `configuration` | string | Default `"full"`; one of `keyword`, `rule_only`, `rule_kg`, `semantic_only`, `semantic_kg`, `hybrid_no_kg`, `full` |

Unknown fields are rejected, both at the top level and inside `worker`, so typos fail loudly.

### Response 200

```json
{
  "configuration": "full",
  "k": 10,
  "display_threshold": 55,
  "worker": {
    "worker_id": "3917d39f-d0c0-46c2-aa34-9158711f68f3",
    "biography": "Niko Nyeri, ni fundi wa umeme. Experience miaka 20, rates from KSh 2000.",
    "skills": ["fundi wa umeme"],
    "location": "Nyeri",
    "availability": "Part-time",
    "rate_expectation": 2000.0
  },
  "enrichment": {
    "terms": [{ "id": "term:fundi umeme", "label": "fundi wa umeme" }],
    "occupations": [{ "id": "http://data.europa.eu/esco/occupation/4910419f-b4af-4f59-b544-9dbebc8a74f0",
                      "label": "electrician" }],
    "unmapped": []
  },
  "results": [
    {
      "rank": 1,
      "posting_id": "979d6da3-3b29-43cd-8e3f-8e612197d124",
      "title": "Electrical fault-finding in an office",
      "description": "Job: electrical fault-finding in an office, Meru. …",
      "location": "Meru",
      "availability": "Part-time",
      "budget": 4700.0,
      "scores": { "composite": 0.698, "rule": 0.8, "semantic": 0.595 },
      "match_score": 70,
      "band": "moderate",
      "rule_components": { "skill_overlap": 1.0, "location": 0.0, "budget_fit": 1.0, "availability": 1.0 },
      "matched_skills": [
        {
          "skill": "http://data.europa.eu/esco/skill/52d6eb67-56c0-4ad7-b5c2-71e7c2362ece",
          "skill_label": "install electricity sockets",
          "source": "informal_term",
          "skill_type": "skill",
          "graph_path": [
            { "source": { "id": "term:fundi umeme", "label": "fundi wa umeme", "type": "InformalTerm" },
              "relation": "MAPS_TO",
              "target": { "id": "http://data.europa.eu/esco/occupation/4910419f-…", "label": "electrician",
                          "type": "Occupation" } },
            { "source": { "id": "http://data.europa.eu/esco/occupation/4910419f-…", "label": "electrician",
                          "type": "Occupation" },
              "relation": "HAS_ESSENTIAL_SKILL",
              "target": { "id": "http://data.europa.eu/esco/skill/52d6eb67-…",
                          "label": "install electricity sockets", "type": "Skill" } }
          ]
        }
      ]
    }
  ],
  "timing_ms": 67.0
}
```

**`null` means "not assessed"; it never means 0.** The API returns `null`, never 0, for:

| Field | Is `null` when |
|---|---|
| `scores.rule` | The configuration has no rule component (`keyword`, `semantic_only`, `semantic_kg`) |
| `scores.semantic` | The configuration has no semantic component (`keyword`, `rule_only`, `rule_kg`) |
| `rule_components` | The configuration has no rule component (the whole object is `null`) |
| `rule_components.<criterion>` | The criterion's field is missing on either side, e.g. `budget_fit` when the worker gave no rate or the posting has no budget. Absent criteria do not count towards `scores.rule` (`docs/scoring-policy.md` §1) |
| `worker.worker_id` | The profile was typed in, not stored |
| `location`, `availability`, `budget` of a result | The posting does not state them (the 200 Job Skill Set postings) |

A real 0 is a real score: e.g. `location: 0.0` means "assessed, different town".

**`matched_skills[].source`** says how the worker came to have the skill:

| `source` | Meaning | Suggested UI text | `graph_path` |
|---|---|---|---|
| `listed` | The worker listed this ESCO skill | "listed by you" | `[]` |
| `text` | The worker's own words, matched literally (not an ESCO skill) | "your own words" | `[]` |
| `informal_term` | Inferred from an informal term the worker used | "inferred via *fundi wa umeme*" (the path's first node) | 2 edges: term → occupation → skill |
| `occupation_label` | Inferred from an ESCO occupation named in the worker's text | "inferred via occupation *electrician*" | 1 edge: occupation → skill |

Every node in `graph_path` carries `id`, `label` and `type` (`InformalTerm`, `Occupation`, `Skill`),
so the UI never needs a second lookup.

**`matched_skills[].skill_type`** is ESCO's own split, `"skill"` or `"knowledge"` (`null` for a
`text` match, which is not an ESCO node). It exists so an explanation can be written in correct
English: a job *needs someone to* install electricity sockets (a skill), but simply *needs*
electrical wiring plans (knowledge).

### Presentation: `match_score`, `band` and `display_threshold`

`composite` is the number the engine ranks and the evaluation measures. `match_score` and
`band` are the same number dressed for a screen, and `display_threshold` is the score below
which the interface shows nothing rather than a bad suggestion.

| Field | Meaning |
|---|---|
| `match_score` | `round(composite * 100)`, an integer 0–100 |
| `band` | `strong` (≥ 80), `moderate` (65–79), `weak` (55–64), `below_threshold` (< 55) |
| `display_threshold` | 55, the lowest `match_score` worth showing |

**These are presentation only.** Ranking, `k` and the order of `results` ignore them entirely,
and `scripts/evaluate.py` never reads them, so no published metric moves when the bands change.
Results below the threshold are still returned, labelled `below_threshold`; the decision to hide
them belongs to the interface. The evidence for the number 55 is in `docs/scoring-policy.md` §6,
and the proof that adding it changed no metric is in `docs/evidence/evaluation_isolation.md`.
Implementation: `apps/api/src/kaziforce_api/matching/bands.py`.

`enrichment.unmapped` lists the worker's skills entries that matched nothing in the knowledge
graph (FR-10). A withheld alias such as *fundi wa stima* appears there.

## `POST /workers`

Stores a worker profile and returns the identifier the database gave it, so the client can
immediately ask for recommendations. The body **is** the worker object of `POST /recommend`,
with the same fields and the same rules.

```json
{
  "biography": "Mimi ni fundi wa umeme, niko Nyeri.",
  "skills": ["fundi wa umeme"],
  "location": "Nyeri",
  "availability": "Part-time",
  "rate_expectation": 2000
}
```

**Response 201**

```json
{
  "worker_id": "e5a7c1d2-…",
  "worker": { "worker_id": "e5a7c1d2-…", "biography": "…", "skills": ["fundi wa umeme"],
              "location": "Nyeri", "availability": "Part-time", "rate_expectation": 2000.0 },
  "enrichment": { "terms": [{ "id": "term:fundi umeme", "label": "fundi wa umeme" }],
                  "occupations": [{ "id": "http://data.europa.eu/esco/occupation/4910419f-…",
                                    "label": "electrician" }],
                  "unmapped": [] }
}
```

When a signed-in worker creates a profile, the account claims it, and `/auth/session` then
reports its `worker_profile_id`. An account may hold one profile: a second attempt is a 409
`already_exists`. A client account creating a profile is a 403.

No name or contact field is accepted: profiles hold no personally identifying information (DR-07).
Duplicate skills entries are collapsed, keeping the first of each. A term the knowledge graph does
not know appears in `enrichment.unmapped` and the profile is still stored (FR-10).

## `GET /workers/me`

The signed-in worker's own profile, in the same shape `POST /workers` returns, so the
profile screen can show what the engine made of their words. 404 while the account has no
profile; 403 for a client.

## `POST /jobs`

Stores a job posting, adds it to the live candidate pool, and returns how the engine understood it.

```json
{
  "title": "Rewire a small shop",
  "description": "We need an electrician in Nyeri to rewire a small shop.",
  "required_skills": ["install electricity sockets", "splice cable"],
  "location": "Nyeri",
  "availability": "Part-time",
  "budget": 2600
}
```

| Field | Type | Rules |
|---|---|---|
| `title` | string | Required, non-empty, at most 255 characters |
| `description` | string | Required, non-empty, at most 4000 characters |
| `required_skills` | string[] | Optional (default `[]`), at most 50 entries of 200 characters |
| `location` | string \| null | Optional, at most 200 characters |
| `availability` | `"Full-time"` \| `"Part-time"` \| `"Weekends"` \| null | Optional |
| `budget` | number \| null | Optional, KES per day, ≥ 0 |

`category` is **not** accepted, and sending it is a 400. The column exists in the schema, but
matching never reads it, so the API does not invite a client to set it.

**Response 201** (identical to `GET /jobs/{posting_id}`)

```json
{
  "posting_id": "7c1f9b40-…",
  "job": { "posting_id": "7c1f9b40-…", "title": "Rewire a small shop", "description": "…",
           "required_skills": ["install electricity sockets", "splice cable"],
           "location": "Nyeri", "availability": "Part-time", "budget": 2600.0 },
  "interpretation": {
    "terms": [],
    "occupations": [{ "id": "http://data.europa.eu/esco/occupation/4910419f-…", "label": "electrician" }],
    "unmapped": [],
    "stated_skills": [
      { "skill": "http://data.europa.eu/esco/skill/52d6eb67-…", "skill_label": "install electricity sockets",
        "source": "listed" }
    ],
    "worker_pool": [
      { "occupation": { "id": "http://data.europa.eu/esco/occupation/4910419f-…", "label": "electrician" },
        "workers": 36,
        "sample": [
          { "describes_as": "fundi wa umeme", "location": "Nairobi - Kasarani",
            "availability": "Part-time", "rate_expectation": 1800.0 }
        ] }
    ]
  },
  "candidate_jobs": 281
}
```

- **`stated_skills` are the posting's own requirements only**, each `listed` (an exact ESCO skill
  label) or `text` (the client's own words). Skills the knowledge graph could infer from the
  occupation are deliberately **not** reported here, because matching uses a posting's stated
  requirements only (`docs/scoring-policy.md` §1). Reporting inferred skills would imply they
  count towards a match when they do not.
- **`worker_pool`** counts stored worker profiles whose own enrichment reaches each occupation this
  posting reaches, so the right phrasing is "workers whose profiles match the *electrician*
  occupation". It is computed from the profiles, never from the dataset's occupational area labels.
  It is `[]` when the posting reaches no occupation.
- **`worker_pool[].sample`** is at most 5 of those workers, as a client may see them: their own
  words and the practical facts, trimmed to 120 characters at a word boundary. It carries **no
  identifier, no score and no ranking**, because a client posting a job has not been matched to
  anyone and must not be shown a league table of workers. `describes_as` is the worker's listed
  skills, or their biography when they listed none.
- **`candidate_jobs`** is the pool size after this posting was added.

## `GET /jobs`

The signed-in client's own postings, newest first, as rows for the postings list. 403 for a
worker. A client who has posted nothing gets `{ "postings": [] }`.

```json
{
  "postings": [
    { "posting_id": "7c1f9b40-…", "title": "Rewire a small shop", "location": "Nyeri",
      "availability": "Part-time", "budget": 2600.0,
      "trades": [{ "id": "http://data.europa.eu/esco/occupation/4910419f-…", "label": "electrician" }] }
  ]
}
```

`trades` is the occupations the posting reaches, and is `[]` when it reaches none. This
endpoint returns **only the client's own** postings, never the 280 seeded ones.

## `GET /jobs/{posting_id}`

The same body as `POST /jobs` returns, for a posting that is already stored. 404 if there is none.

## Errors

Every error has the same shape, and no error ever includes a stack trace:

```json
{ "error": { "code": "invalid_request", "message": "k must be an integer from 1 to 50", "field": "k" } }
```

| Status | `code` | When | `field` |
|---|---|---|---|
| 400 | `invalid_request` | Body not a JSON object; an invalid or unknown field; a malformed phone number, PIN or role | The offending field, when there is one (e.g. `k`, `worker.availability`, `phone`) |
| 401 | `unauthenticated` | The endpoint needs a session and there is none, or it has expired | — |
| 401 | `invalid_credentials` | The phone number or PIN is wrong. The message is the same either way, so it never reveals whether a number is registered | — |
| 403 | `forbidden` | Signed in as the other role, or a worker asking for matches before creating a profile | — |
| 409 | `already_exists` | That phone number already has an account, or that account already has a profile | `phone` |
| 423 | `locked` | Five wrong PINs; the account is locked for 15 minutes | — |
| 404 | `not_found` | `worker_id` is not a stored worker, `posting_id` is not a stored posting, or the URL is unknown | `worker_id` or `posting_id` |
| 501 | `not_supported` | `POST /workers` or `POST /jobs` while the server reads the frozen CSVs (`KAZIFORCE_PROFILE_SOURCE=csv`) | — |
| 405 | `method_not_allowed` | E.g. `GET /recommend` | — |
| 503 | `not_ready` | The engine is still loading; a `Retry-After: 5` header is set | — |
| 500 | `internal_error` | Anything unexpected; the details go to the server log only | — |
