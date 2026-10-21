# Web

Next.js / React / TypeScript interface for workers and clients (proposal
Section 3.8.6, IR-01). It talks to `apps/api` only through its Flask REST API,
exchanging JSON (IR-02); the contract is `docs/api.md`.

## Screens

| Route | Screen | Wireframe |
|---|---|---|
| `/` | Choose: find work, or post a job | — |
| `/worker` | Create a worker profile (FR-01) | `01-worker-profile.html` |
| `/worker/[workerId]/matches` | Ranked jobs with score components (FR-08) | `03-recommendations.html` |
| `/worker/[workerId]/matches/[postingId]` | Why this match: criteria, matched skills, graph paths (FR-09) | `04-explanation.html` |
| `/jobs/new` | Post a job (FR-02) | `02-job-posting.html` |
| `/jobs/[postingId]` | How the posting was understood, and the matching worker pool | `05-posting-interpretation.html` |

Identifiers live in the URL, so every screen survives a refresh and can be
shared. Nothing is kept in browser storage.

## Running it

The API must be running first (it serves the data, and the browser calls it
directly):

```bash
# in the repository root, with the Python environment active
flask --app kaziforce_api.app run          # http://127.0.0.1:5000
```

```bash
cd apps/web
npm install
npm run dev                                # http://localhost:3000
```

The API's address comes from `NEXT_PUBLIC_API_BASE` and defaults to
`http://127.0.0.1:5000`. The API allows browser requests from
`http://localhost:3000` and `http://127.0.0.1:3000`; `KAZIFORCE_CORS_ORIGIN` replaces
that list and takes comma-separated origins.

**The engine takes about half a minute to load** after the API starts, while
the knowledge graph and the language model are read in. During that time the
API answers 503 and the interface shows a banner explaining the wait. Forms
stay usable: the API client waits out a 503 by itself.

## Browser tests (NFR-05)

End-to-end tests drive the real interface against the real API in **Chromium and WebKit**,
the engines behind Chrome and Safari. They are run by hand, not in CI, which has neither a
database nor the language model.

```bash
npx playwright install chromium webkit     # once
npm run e2e                                # with the API running
npm run e2e:screenshots                    # refresh docs/evidence/screens/
```

They store real profiles and postings through the API. Afterwards, clear them with
`python scripts/seed_database.py --reset` in the repository root and restart the API,
which holds the candidate pool in memory.

**On macOS, the API is at `127.0.0.1:5000`, not `localhost:5000`.** AirPlay Receiver
listens on port 5000 over IPv6 and answers 403, while Flask binds IPv4 only.

## Checks

```bash
npm run type-check     # tsc --noEmit
npm run lint           # eslint (next config)
npm test               # vitest
npm run build          # production build
```

## Conventions worth knowing

- **`null` is never 0.** The API returns `null` for a score component a
  configuration does not use, and for a rule criterion whose field is missing
  on the profile or the posting. `ScoreValue` and `ScoreBar` are the only
  places a score becomes text or a bar, and they render `null` as *Not
  assessed* with an empty hatched track, never as 0%. `__tests__/ScoreValue.test.tsx`
  renders `null` and `0` side by side and requires them to differ.
- **Matched skills say where they came from.** `source` is one of `listed`,
  `text`, `informal_term` or `occupation_label`, and each gets its own words
  and icon: "listed by you", "your own words", "inferred via *fundi wa
  umeme*", "inferred via occupation *electrician*". An unknown source falls
  back to a neutral badge rather than breaking the page.
- **One configuration.** The interface always asks for the full system. There
  is no configuration selector: the keyword baseline's BM25 scores are not
  bounded by 1 and cannot be shown as percentages.
- **A posting's own skills only.** The posting screen shows the skills the
  client listed, never skills the knowledge graph could infer from the
  occupation, because matching uses stated requirements only
  (`docs/scoring-policy.md` §1).
- **Dynamic routes keep a static shell.** The heading of each dynamic page
  renders immediately and the data streams in behind a `<Suspense>` boundary,
  which is what Next.js 16 expects of a route that reads `params`.

`vite` is a direct dev dependency on purpose: without it, `@vitejs/plugin-react`
can resolve a different `vite` from outside the project.
