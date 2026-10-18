# REST API

Flask API between the web app and the recommendation engine (IR-02). JSON in, JSON out.
Implementation: `apps/api/src/kaziforce_api/app.py` (routes, validation) and
`service.py` (engine, response building). Tests: `tests/test_api.py`.

Run it:

    flask --app kaziforce_api.app run          # http://127.0.0.1:5000

The engine loads in the background at startup: the knowledge graph, 280 postings, the
all-MiniLM-L6-v2 model and the job embeddings, taking about 20–30 s on CPU. Until it is ready,
`/health` reports `"ready": false` and `/recommend` answers 503. After that, a request takes
well under 0.2 s.

**CORS.** Browser requests are allowed from `http://localhost:3000` (the Next.js dev server).
Set `KAZIFORCE_CORS_ORIGIN` to change it. Other origins get no CORS headers.

## `GET /health`

```json
{ "status": "ok", "ready": true }
```

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
| `worker_id` | string | A stored worker. For now this means the development split of the synthetic dataset; #41 moves it to PostgreSQL |
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

### Errors

Every error has the same shape, and no error ever includes a stack trace:

```json
{ "error": { "code": "invalid_request", "message": "k must be an integer from 1 to 50", "field": "k" } }
```

| Status | `code` | When | `field` |
|---|---|---|---|
| 400 | `invalid_request` | Body not a JSON object; both or neither of `worker_id` and `worker`; an invalid or unknown field | The offending field, when there is one (e.g. `k`, `worker.availability`) |
| 404 | `not_found` | `worker_id` is not a stored worker; or an unknown URL | `worker_id` for unknown workers |
| 405 | `method_not_allowed` | E.g. `GET /recommend` | — |
| 503 | `not_ready` | The engine is still loading; a `Retry-After: 5` header is set | — |
| 500 | `internal_error` | Anything unexpected; the details go to the server log only | — |
