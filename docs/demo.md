# Running the demo

The sequence below was rehearsed end to end on 2026-10-20 (macOS 15.8.1, Intel
Core i5-8279U, PostgreSQL 14.19). Each step shows what it should print.

Two terminals, both in the repository root, with the Python environment active
(`. venv/bin/activate`).

## Before the demo

### 1. Check the schema is current

```bash
python -m kaziforce_api.data.migrate
```
```
Database is up to date.
```

If it instead prints `Applied: 0002_application_store`, that is fine: the
migration had not run yet.

### 2. Reset and seed

```bash
python scripts/seed_database.py --reset
```
```
Deleted: worker_skill 530, job_required_skill 3836, worker_profile 216, job_posting 280, skill 1758
Seeded: skill 1758, worker_profile 216, worker_skill 530, job_posting 280, job_required_skill 3836
```

The `Deleted` line counts whatever was there before, so it changes between runs;
the `Seeded` line is always exactly these numbers. On a first run the `Deleted`
line is absent.

### 3. Start the API (terminal 1)

```bash
flask --app kaziforce_api.app run
```
```
 * Serving Flask app 'kaziforce_api.app'
 * Debug mode: off
 * Running on http://127.0.0.1:5000
```

**Wait about 30 seconds** (27 s when rehearsed) while the knowledge graph, the
280 postings and the language model load. Until then the interface shows a
banner saying so. Check it is ready:

```bash
curl -s http://127.0.0.1:5000/health
```
```json
{"status":"ok","ready":true,"candidate_jobs":280}
```

Use `127.0.0.1`, not `localhost`: on macOS, AirPlay Receiver holds port 5000
over IPv6 and answers 403.

### 4. Start the interface (terminal 2)

```bash
cd apps/web && npm run dev
```
```
- Local:         http://localhost:3000
✓ Ready in 827ms
```

Open **http://localhost:3000**. Use `localhost:3000` here, not `127.0.0.1:3000`
— both are allowed, but `localhost` is what the browser address bar will keep.

## The demo path

1. **Find work** → describe a worker in their own words, e.g.
   *"Mimi ni fundi wa umeme, nina uzoefu wa miaka mitano. Niko Nyeri."*, skill
   *fundi wa umeme*, location Nyeri, Part-time, 2000.
2. **Your matches** shows "Understood as **electrician**, from the wording
   *fundi wa umeme*", then ten ranked jobs. Rehearsed top three:
   *Electrical fault-finding in an office*, *Install security lights in a
   compound*, *House wiring for new rental units*.
3. **Why this match?** shows the composite score, the rule and semantic
   components, the four criteria, and each matched skill with its path:
   *fundi wa umeme* → maps to → electrician → has essential skill →
   *install electricity sockets* → required by → this job.
4. **Post a job** → e.g. *Rewire a small shop*, requiring
   *install electricity sockets*, in Nyeri, budget 2600.
5. **Your job posting is live** shows the occupation it was understood as, the
   skills you listed, and how many registered profiles match that occupation.

Two things worth showing deliberately:

- **A term the vocabulary does not know.** Enter *fundi wa stima* as the skill.
  The profile is still accepted, and the matches screen says
  "Not recognised: *fundi wa stima*. It is kept as written and matched word for
  word." That is the honest cold-start case, and it is the system's main
  limitation.
- **A criterion that cannot be assessed.** Leave the daily rate blank. The
  explanation screen then shows "Not assessed" against *Budget against your
  rate*, not 0%, with the reason.

## What the demo writes to the database

| Action | Effect |
|---|---|
| Browsing, ranking, opening explanations | **Nothing is written.** |
| Submitting a worker profile | One `worker_profile` row, its `worker_skill` rows, and a `skill` row for any wording not seen before |
| Posting a job | One `job_posting` row and its `job_required_skill` rows. The posting also joins the live candidate pool, so `candidate_jobs` goes from 280 to 281 and stays there until the API restarts |
| — | `match_score` stays empty: the interface does not write ranking rows. Only `scripts/run_recommendation.py` does |

So after a demo with one profile and one posting, expect 217 worker profiles
and 281 postings. Nothing is corrupted, and the evaluation is unaffected: it
reads the frozen CSV files, never the database.

## After the demo

```bash
python scripts/seed_database.py --reset
```

Then **restart the API**, because it holds the candidate pool in memory and
would otherwise keep serving the postings you added.

## If something goes wrong

| Symptom | Cause and fix |
|---|---|
| The banner says "Cannot reach the matching service" | The API is not running, or it is not on `127.0.0.1:5000`. Check `curl http://127.0.0.1:5000/health`. |
| The banner says "Preparing the matching engine…" and stays | Still loading; it takes about 30 s. If it lasts minutes, check the API terminal for an error. |
| Submitting gives "this server cannot store new profiles" | The API is reading the CSV files instead of PostgreSQL. Make sure `DATABASE_URL` is set in `.env` and `KAZIFORCE_PROFILE_SOURCE` is not set to `csv`. |
| Submitting gives a 500, or the API fails to start with "no job postings" | The database is not seeded. Run step 2. |
| The same job appears several times at the top | Postings added in an earlier demo or test run. Run step 2 and restart the API. |
| `curl http://localhost:5000/health` returns 403 | macOS AirPlay Receiver. Use `127.0.0.1:5000`, or turn it off in System Settings → General → AirDrop & Handoff. |
