# Interface screenshots

Captured by `apps/web/e2e/screenshots.spec.ts` (`npm run e2e:screenshots`) from the
running interface and API, in both browser engines. The pages are real: every score,
skill badge and graph path comes from the API.

| File | Screen | Wireframe |
|---|---|---|
| `00-landing.png` | Choose: find work, or post a job | — |
| `01-worker-profile.png` | Create a worker profile, filled in (FR-01) | `01-worker-profile.html` |
| `02-job-posting.png` | Post a job, filled in (FR-02) | `02-job-posting.html` |
| `03-recommendations.png` | Ranked jobs with score components and skill provenance (FR-08) | `03-recommendations.html` |
| `04-explanation.png` | Why this match: criteria, matched skills, graph paths (FR-09) | `04-explanation.html` |
| `05-posting-interpretation.png` | How the posting was understood, and the worker pool | `05-posting-interpretation.html` |

`chromium/` and `webkit/` are the engines behind Chrome and Safari (NFR-05). The two
sets differ only in font rendering and form-control styling.

The profile used throughout is *"Mimi ni fundi wa umeme, nina uzoefu wa miaka mitano.
Niko Nyeri."*, with the single skill *fundi wa umeme*. The knowledge graph maps that
term to the ESCO occupation **electrician**, which is why every matched skill is
labelled "inferred via fundi wa umeme".
