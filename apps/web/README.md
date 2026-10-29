# Web

Next.js / React / TypeScript interface for workers and clients (proposal
Section 3.8.6, IR-01). It talks to `apps/api` only through its Flask REST API,
exchanging JSON (IR-02); the contract is `docs/api.md`.

## Screens

Built to the approved designs in `docs/UI views/`.

| Route | Screen | Design |
|---|---|---|
| `/` | Sign in with a phone number and 4-digit PIN | `sign_in.png` |
| `/create-account` | Create an account, as a worker or a client | `create_account.png` |
| `/worker/profile` | Describe your work (FR-01) | `create_worker_profile_view.png` |
| `/worker/matches` | Ranked jobs with match score and band (FR-08), or nothing above the threshold | `job_matches_for_worker_view.png`, `no_matches.png` |
| `/worker/matches/[postingId]` | Why this job suits you, in plain words, with the technical detail behind a disclosure (FR-09, FR-10) | `worker_explanation_view.png` |
| `/client/post` | Post a job (FR-02) | `job_posting_creation.png` |
| `/client/postings/[postingId]` | How the posting was understood, and the trade list | `job_posted_confirmation.png` |
| `/client/postings` | A client's own postings | — (composed from the confirmation row style) |

A worker's own identifier is no longer in the URL: the session says who they
are, and the interface asks for "my" profile and matches. A posting identifier
stays in the URL, so an explanation can be refreshed and shared. Nothing is kept
in browser storage; the session is an `HttpOnly` cookie the interface cannot
read, so it asks `/auth/session` instead.

Each screen is guarded by role. A signed-out visitor is sent to `/`, and someone
signed in as the other role is sent to their own home. The guard waits for the
session answer before redirecting, so a refresh never throws a signed-in person
out.

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
npm run dev -- --hostname 127.0.0.1        # http://127.0.0.1:3000
```

**Use `127.0.0.1` for both, not `localhost` for one and `127.0.0.1` for the
other.** The session cookie is `SameSite=Lax`, and the browser treats
`localhost:3000` and `127.0.0.1:5000` as different sites, so it would withhold
the cookie and every signed-in request would answer 401. The API client derives
the API host from the page's own hostname for exactly this reason, so whichever
spelling the page is served from, the API is called with the same one.

`NEXT_PUBLIC_API_BASE` overrides that derivation when the API is somewhere else.
The API allows browser requests from `http://localhost:3000` and
`http://127.0.0.1:3000`; `KAZIFORCE_CORS_ORIGIN` replaces that list and takes
comma-separated origins.

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

`e2e/core-workflow.spec.ts` covers nine journeys in each engine: a worker signing
up, describing their work and reading an explained match; a worker with no rate
being told it could not be checked rather than scored zero; a worker whose
wording is outside the vocabulary being told so plainly; a client posting a job
and seeing how it was understood; a client's own postings being listed; signing
out and back in; a wrong PIN; a signed-out visitor being redirected; and a check
that no PIN is left in the page after signing up.

The test server is pinned to `127.0.0.1` for the cookie reason above, including
the `--hostname` it passes to `next dev`.

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

- **A criterion with nothing to compare is said in words, never as 0.** Since
  the interface no longer shows a criterion table, an unassessed criterion
  appears as a sentence — "This job doesn't give a budget, so we couldn't
  compare it with your rate." — in its own "What we couldn't check" section. It
  is never a zero, a dash or an empty bar, and it is never phrased as a failure.
  The backend decides which side was silent; `__tests__/Explanation.test.tsx`
  requires that section to contain no bare 0 and no word like "failed".
- **Provenance is stated in words, not badges.** The four labels ("Listed by
  you", "Your own words", "Inferred via *fundi wa umeme*", "Inferred via
  occupation: *electrician*") were part of the technical detail and went with
  it. What remains on screen is the vocabulary note — "You described yourself as
  a *fundi wa umeme*. We matched that to the trade *electrician*." — and the
  per-skill `source` is still in the API payload for anyone who needs it.
- **The word "confidence" appears nowhere.** A match score is not a
  probability, and calling it one would overstate what the engine knows. Unit
  tests assert the word is absent from the score badge and the explanation.
- **Plain words only, and the interface writes none of them.** The explanation
  is generated by the API (`apps/api/.../explainability/`) and rendered exactly
  as it arrives. `Explanation.tsx` has no sentence-building logic, and there is
  no technical-detail section: a worker is shown the sentences, never the
  component scores, the criterion table or the raw graph path. The structured
  payload is still returned on every result and is recorded for the thesis in
  `docs/evidence/explanation_payload.md`. The unit test feeds the component text
  no sentence-builder would produce and requires it to reach the screen
  unchanged.
- **Below 55 is nothing, not a bad match.** The API labels every result with a
  `band` and reports its `display_threshold`. A worker with nothing above it
  sees "No strong matches yet" and an invitation to edit their profile, rather
  than a list of poor suggestions. The threshold is presentation only; the
  evaluation never sees it.
- **One configuration.** The interface always asks for the full system. There
  is no configuration selector: the keyword baseline's BM25 scores are not
  bounded by 1 and cannot be shown as percentages.
- **A posting's own skills only.** The posting screen shows the skills the
  client listed, never skills the knowledge graph could infer from the
  occupation, because matching uses stated requirements only
  (`docs/scoring-policy.md` §1).
- **A client has an account, not a profile.** Clients are not matched, so there
  is nothing to enrich and no profile screen. The client navigation is "Post a
  job | My postings".
- **A client never sees a worker's score or rank.** The trade list on the
  confirmation screen shows at most five workers in their own words with their
  location, availability and rate — no identifier, no score, no ordering.
- **Dynamic routes keep a static shell.** The heading of each dynamic page
  renders immediately and the data streams in behind a `<Suspense>` boundary,
  which is what Next.js 16 expects of a route that reads `params`.
- **A route stays mounted after you leave it.** Next keeps the previous route in
  a hidden Activity so back navigation can restore its state. Two consequences:
  the sign-in and create-account forms clear the PIN from state before
  navigating away, so it is not left in the DOM; and a browser test must scope
  its locators to `main:visible`, because every label otherwise exists twice.

`vite` is a direct dev dependency on purpose: without it, `@vitejs/plugin-react`
can resolve a different `vite` from outside the project.
