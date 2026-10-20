# REST API

Flask API between the web app and the recommendation engine (IR-02). JSON in, JSON out.
Implementation: `apps/api/src/kaziforce_api/app.py` (routes, validation) and
`service.py` (engine, response building). Tests: `tests/test_api.py` and
`tests/test_api_db.py`.

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | Readiness and the size of the candidate pool |
| POST | `/recommend` | Ranked jobs for a stored worker or a typed-in profile |
| POST | `/workers` | Store a worker profile; returns its identifier and enrichment |
| POST | `/jobs` | Store a job posting, add it to the candidate pool, return how it was understood |
| GET | `/jobs/{posting_id}` | How a stored posting was understood |

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
origin gets no CORS headers, so the browser blocks the response.

**On macOS, use `127.0.0.1:5000`, not `localhost:5000`.** AirPlay Receiver listens on port
5000 over IPv6 and answers 403, while Flask binds IPv4 only, so `localhost` can reach the
wrong service. Turn AirPlay Receiver off in System Settings → General → AirDrop & Handoff,
or keep using `127.0.0.1`.

## `GET /health`

```json
{ "status": "ok", "ready": true, "candidate_jobs": 280 }
```

`candidate_jobs` is 0 until the engine is ready, and grows as postings are stored.

## `POST /recommend`

Ranked jobs for one worker, either a **stored** worker (`worker_id`) or a **typed-in** profile
(`worker`). Send exactly one of the two.

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
      "rule_components": { "skill_overlap": 1.0, "location": 0.0, "budget_fit": 1.0, "availability": 1.0 },
      "matched_skills": [
        {
          "skill": "http://data.europa.eu/esco/skill/52d6eb67-56c0-4ad7-b5c2-71e7c2362ece",
          "skill_label": "install electricity sockets",
          "source": "informal_term",
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

No name or contact field is accepted: profiles hold no personally identifying information (DR-07).
Duplicate skills entries are collapsed, keeping the first of each. A term the knowledge graph does
not know appears in `enrichment.unmapped` and the profile is still stored (FR-10).

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
        "workers": 36 }
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
- **`candidate_jobs`** is the pool size after this posting was added.

## `GET /jobs/{posting_id}`

The same body as `POST /jobs` returns, for a posting that is already stored. 404 if there is none.

## Errors

Every error has the same shape, and no error ever includes a stack trace:

```json
{ "error": { "code": "invalid_request", "message": "k must be an integer from 1 to 50", "field": "k" } }
```

| Status | `code` | When | `field` |
|---|---|---|---|
| 400 | `invalid_request` | Body not a JSON object; both or neither of `worker_id` and `worker`; an invalid or unknown field | The offending field, when there is one (e.g. `k`, `worker.availability`) |
| 404 | `not_found` | `worker_id` is not a stored worker, `posting_id` is not a stored posting, or the URL is unknown | `worker_id` or `posting_id` |
| 501 | `not_supported` | `POST /workers` or `POST /jobs` while the server reads the frozen CSVs (`KAZIFORCE_PROFILE_SOURCE=csv`) | — |
| 405 | `method_not_allowed` | E.g. `GET /recommend` | — |
| 503 | `not_ready` | The engine is still loading; a `Retry-After: 5` header is set | — |
| 500 | `internal_error` | Anything unexpected; the details go to the server log only | — |
