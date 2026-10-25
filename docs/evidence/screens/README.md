# Interface screenshots

Captured by `apps/web/e2e/screenshots.spec.ts` (`npm run e2e:screenshots`) from the
running interface and API, in both browser engines. The pages are real: every score,
matched skill and graph path comes from the API.

The file names follow the approved designs in `docs/UI views/`, so each figure can be
set beside the design it was built from.

| File | Screen | Design | Requirement |
|---|---|---|---|
| `01-sign_in.png` | Sign in with a phone number and 4-digit PIN | `sign_in.png` | — |
| `02-create_account.png` | Create an account, filled in | `create_account.png` | — |
| `03-create_worker_profile_view.png` | Describe your work, filled in | `create_worker_profile_view.png` | FR-01 |
| `04-job_matches_for_worker_view.png` | Ranked jobs with match score and band | `job_matches_for_worker_view.png` | FR-08 |
| `05-worker_explanation_view.png` | Why this job suits you, technical detail opened | `worker_explanation_view.png` | FR-09, FR-10 |
| `06-no_matches.png` | Nothing above the display threshold | `no_matches.png` | FR-08 |
| `07-job_posting_creation.png` | Post a job, filled in | `job_posting_creation.png` | FR-02 |
| `08-job_posted_confirmation.png` | How the posting was understood, and the trade list | `job_posted_confirmation.png` | FR-03 |
| `09-client_postings_list.png` | A client's own postings | — (composed from the confirmation row style) | FR-02 |

`chromium/` and `webkit/` are the engines behind Chrome and Safari (NFR-05). The two
sets differ only in font rendering and form-control styling.

The worker used for screens 03–05 describes their work as *"fundi wa umeme, wiring,
solar installation"*. The knowledge graph maps *fundi wa umeme* to the ESCO occupation
**electrician**, which is why matched skills are labelled "Inferred via fundi wa umeme".

Screen 06 uses *"fundi wa stima"*, an alias deliberately withheld from the knowledge
graph, so the worker reaches no trade and nothing clears the display threshold of 55.

Screen 07's posting names a *fundi bomba* — the accepted plumber alias in the frozen
vocabulary — in its description. Matching reads the description and the required
skills, not the title.

The captures of the earlier four-screen interface were removed when those routes were
replaced; they remain in the git history up to commit `1ae4e60`.
