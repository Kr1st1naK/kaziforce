# Privacy, keys and the way to HTTPS

What the system stores about a person, how it is protected, who can read it, and what is left
to do before it is deployed. Limitations are numbered in `docs/limitations.md` (items 26, 28 and
32–40); this file is the how, and the runbook.

## What is stored, and where

| Data | Where | Protection |
|---|---|---|
| Phone number | `account.phone_enc`, `account.phone_hash` | `phone_enc` is AES-256-GCM, random nonce per value, `v1:` key-version prefix. `phone_hash` is HMAC-SHA256 under a *separate* key; it is the sign-in lookup key and is unique |
| First and last name (workers only) | `account.first_name_enc`, `account.last_name_enc` | AES-256-GCM, as above. On the account, never on `worker_profile` |
| Consent to be shown | `account.contact_consent`, `consent_changed_at` | A flag, off unless the worker turned it on. The database refuses it being on without a name |
| PIN | `account.pin_hash`, `pin_salt`, `pin_iterations` | PBKDF2-HMAC-SHA256, 600,000 iterations, per-account salt. Unchanged by this work |
| Session token | `session.token_hash` | SHA-256 of the token; the token itself is only in the cookie |
| Worker profile (words, location, availability, rate) | `worker_profile`, `worker_skill` | Not personal data in the sense of DR-07: no name, no number. Stored in clear, as the matching needs it |
| Worker public id | `worker_profile.public_id` | A random UUID, separate from the internal `worker_id`. Handed out only for a worker who has a name and has consented |

Nothing personal is in the matching data. A name never reaches the embedding, the enrichment or the
scoring: those read a worker's `biography` and `skills`, which come from `worker_profile`, and the
account columns are joined in only after matching, to draw a card or a page
(`tests/test_api_contact.py::test_recommend_never_carries_a_name_or_a_phone`).

## Where a value is decrypted

Four places, each a method of `AccountStore` (`data/accounts.py`), and nowhere else in the running app:

1. `session_account`: the signed-in person's **own phone number**, so they can be shown it. Any role, every authenticated request.
2. `own_contact`: a worker's **own name**, on their profile (`GET` and `PUT /workers/me`).
3. `consented_cards`: the **first and last name** of up to five workers who have a name and have consented, to draw the cards on a client's job-posted screen. This is a third place beyond the two named in the task brief, and it exists because a card shows the name.
4. `consented_contact`: **name and phone** of one consenting worker, for `GET /workers/<public_id>` (signed-in clients only).

Places 3 and 4 skip any worker without a name or without consent. Offline, `backfill_contact.py` decrypts during the migration check and the rollback. No decrypted value is logged, put in a URL, or put in an error message, and the tests assert it.

## Keys

Two secrets, both in the server's environment and never in the repository or the database:

| Variable | Used for | Format |
|---|---|---|
| `KAZIFORCE_FIELD_KEY` | AES-256-GCM for phone and names | 32 random bytes, URL-safe base64 |
| `KAZIFORCE_PHONE_HMAC_KEY` | The `phone_hash` lookup | at least 32 random bytes, URL-safe base64 |

Generate them with:

    python -m kaziforce_api.crypto

It prints two `NAME=value` lines. Put them in `.env` (gitignored) or, in a deployment, in the host's secret store. `.env.example` has empty placeholders. Use different values for every environment, and never reuse a key that has appeared in a chat, a ticket or a commit.

**Refusing to start.** Outside development, the app will not start without both keys, nor without `KAZIFORCE_CORS_ORIGIN`. "Development" is `KAZIFORCE_ENV` (or, if that is unset, `FLASK_ENV`) set to `development` or `test`; anything else, including nothing at all, is production. In development a missing key falls back to a fixed, public one and logs a warning: that protects nothing, and exists so a fresh checkout runs. **Set real keys even in development if the database holds real numbers.**

**Losing a key loses the data.** Without `KAZIFORCE_PHONE_HMAC_KEY` no one can sign in; without `KAZIFORCE_FIELD_KEY` no one can be shown a number or a name. Back the keys up separately from the database backups.

**Rotation is not built.** The `v1:` prefix is there so a `v2` key can be added and old values still decrypt (`FieldCipher` already takes several keys). What is missing is the script that re-encrypts every row under `v2`, and one that recomputes `phone_hash` under a new HMAC key (possible, because `phone_enc` can be decrypted first). Until then the keys do not rotate. See limitations item 34.

## Migrating an existing database (runbook)

The existing accounts hold their phone number in a plaintext `phone` column. The migration encrypts it, checks that the encrypted copy decrypts to the same number, and only then drops the plaintext. It was rehearsed on a copy of the development database (55 accounts, 247 profiles): see the verification notes at the end.

**1. Stop the API.** Until the backfill has run, existing accounts have no `phone_hash` and cannot sign in.

**2. Back up.**

    pg_dump -Fc "$DATABASE_URL" -f kaziforce-before-0004.dump

This file holds the plaintext phone numbers. Keep it somewhere only you can read, and delete it once the migration is verified.

**3. Set the keys** in the environment the commands below run in (they are the same keys the API will use).

**4. Apply 0004.**

    python -m kaziforce_api.data.migrate

It adds the new columns and the worker `public_id`, then stops at 0005 with *"accounts still lack an encrypted phone"*. That stop is the guard doing its job.

**5. Encrypt and verify.**

    python -m kaziforce_api.data.backfill_contact

It encrypts every account, then decrypts each one again, recomputes the hash and compares both with the plaintext. It exits non-zero, and tells you not to continue, if any account does not match. It prints counts only, never a number. Safe to run twice.

**6. Drop the plaintext.**

    python -m kaziforce_api.data.migrate

Applies 0005, which refuses to run unless every account has an encrypted phone.

**7. Start the API and sign in** as an existing account. Existing worker accounts have no name and are not consenting: their cards stay anonymous until the worker adds a name on their profile and ticks the agreement.

**Roll back.**

- *Before step 6*, the plaintext column is still there. Stop the API, deploy the previous code, and set aside the new columns (the previous code ignores them). Accounts created after 0004 have no plaintext phone: run the command below first.
- *After step 6*, or if any account was created after 0004:

      python -m kaziforce_api.data.backfill_contact --restore-plaintext

  This re-creates `phone` and fills it from `phone_enc` (needs the same keys), loosens the `NOT NULL` on the new columns so the previous code can insert, and forgets that 0005 ran. Then deploy the previous code. Or restore the dump from step 2, which loses anything written since.

Both ways back were tested (`tests/test_contact_migration.py`).

### What the rehearsal showed

On a restored copy of the development database in a scratch PostgreSQL on port 5433 (the real database was not touched): 0004 applied; 0005 refused with the expected message; the backfill encrypted and verified 55 of 55 accounts; 0005 then applied and `phone` was gone. With the API on the migrated copy, 53 of the 55 accounts signed in with PIN 4821 through the hash (the other two were refused with 401; they were presumably made with a different PIN, so this check could not use them), with the correct role each time.

## Logging: what was found

- `app.py` logs one thing: `logging.exception("unhandled error")`. That is a traceback, not a request. A database error can carry a `DETAIL` line naming a key value, and the plaintext `phone` column used to be the one that would have (a duplicate number). With `phone_hash` in its place, such a line now names a hash. Nothing else in the file logs.
- `service.py` logs the internal `worker_id` when a ranking cannot be recorded. A UUID, not personal data.
- `data/accounts.py` logs, at error level, a fixed sentence when a stored value will not decrypt (a wrong key), never the value, and never which account.
- Flask's own request log (and Werkzeug's, in development) records method, path and status for each request. The path of a profile view is `/workers/<public_id>`, so **the access log records which client address viewed which worker's page**. An opaque id, but it ties a viewer to a worker. A deployment should decide how long it keeps access logs.
- No code prints request bodies. Error messages name a field and a rule, never the value sent.
- `tests/test_api_contact.py::test_nothing_personal_reaches_the_logs` runs the whole flow at DEBUG and asserts that no phone, name or PIN appears in what the app's loggers wrote. It exercises the application's loggers; it cannot see Werkzeug's access log, which the test client bypasses.

## The PIN: a proposal, not built

A 4-digit PIN has 10,000 values, so PBKDF2 cannot protect it from someone holding a copy of the database: they try all 10,000 offline, once per account, in seconds. A **server-side pepper** moves the secret out of the database:

    stored = PBKDF2( HMAC-SHA256(pepper, pin), salt, iterations )

with `pepper` a 32-byte secret in the environment, like the keys above. A leaked database without the pepper is then useless for guessing.

**Upgrade on next login.** Add a `pin_scheme` column (0 = today, 1 = peppered). When someone signs in and their PIN verifies under scheme 0, re-hash it under scheme 1 and store both. No one is locked out, no PIN is needed in advance, and every account that signs in is protected from then on.

**Trade-offs**

- It protects against *a database leak alone* (a stolen backup, a SQL injection). It does not protect against a server compromise, because the attacker then has the pepper and the data. The 4-digit space is still tiny once the pepper is known.
- Accounts that never sign in again stay on scheme 0, and a dump taken before the upgrade is still weak for them. A cutoff (force a reset after N months) closes that, at the cost of locking out the inactive.
- The pepper becomes something that cannot be lost: lose it and every upgraded PIN fails. There is no PIN recovery today, so a loss means every account needs a manual reset. It needs a backup with the other keys.
- Rotating the pepper is the same upgrade-on-login move again, with `pin_scheme = 2`, and both peppers held while it runs.
- The cost per sign-in is one HMAC: negligible next to 600,000 PBKDF2 iterations.
- It does not help with *online* guessing, which is limited only by the five-try lockout (fifteen minutes) and has no per-address limit. A longer PIN, or an SMS code, would help more than any hashing.

Recommendation: do it with the deployment, with the pepper stored and backed up alongside the field keys, and pair it with a reset path (SMS) so that a lost PIN or pepper is recoverable. This is limitations item 37.

## The session token on the client

How it is stored now: the API sets the session in an **HttpOnly, SameSite=Lax cookie** (`kaziforce_session`, 7 days; `Secure` in production, or whenever the request is HTTPS). The web app's `fetch` calls use `credentials: "include"` and nothing else. JavaScript never sees the token, and nothing is kept in `localStorage` or `sessionStorage` (`apps/web/lib/api.ts`; a test asserts no PIN is left in the page).

That is the safest of the common options, because a script injected into the page cannot read an HttpOnly cookie, which it could from storage. For production over HTTPS I would keep it and tighten it:

1. **Prefix it `__Host-`**: the browser then refuses it unless it is `Secure`, has `Path=/` and no `Domain`, which stops a sibling subdomain from planting one.
2. **Shorten it**: for example a 12-hour absolute lifetime with a 30-minute idle timeout, instead of 7 days. A phone is shared, lost and borrowed.
3. **Rotate it on sign-in** (already a new token each time) and **on any change of consent or PIN**, and revoke the others. Revocation by deleting the `session` row already works.
4. **Add CSRF protection.** `SameSite=Lax` is the only defence today. Check `Origin` on every state-changing request (cheap and strong), or send a custom header the browser will not add cross-site.
5. **Put the app and the API on one site.** A `SameSite` cookie is only sent when both are the same *site*. `app.example.org` and `api.example.org` are; two unrelated domains are not. Serving the API under `/api` on the web app's own origin is simpler still and removes CORS.
6. Do not move it into JavaScript-readable storage, or into a JWT in a header, for convenience.

## Preparing for HTTPS (not done)

Done now: the API names its one allowed origin and refuses to start in production without it (never `*`, since it sends cookies); every response carries `X-Content-Type-Options`, `X-Frame-Options: DENY`, `Referrer-Policy`, a closed `Content-Security-Policy` and `Cache-Control: no-store`; `Strict-Transport-Security` is sent in production only; the session cookie is `Secure` in production. The Next app sends the first three of those headers and HSTS in a production build. Responses carrying a worker's number are never cacheable.

**Plain-HTTP assumptions still in the code or the docs**

1. `NEXT_PUBLIC_API_BASE` defaults to `http://127.0.0.1:5000` (`apps/web/lib/api.ts`), and Next inlines it at build time, so a production build must be given an `https://` address.
2. The API's default CORS origins are the two `http://…:3000` development addresses; production must set `KAZIFORCE_CORS_ORIGIN` (enforced).
3. `flask run` is the development server. A deployment needs a real WSGI server behind a TLS-terminating proxy. Behind one, Flask's `request.is_secure` is false unless the proxy's headers are trusted (`ProxyFix`); the production cookie is forced `Secure` so that does not matter for it, but anything else reading `is_secure` would.
4. `DATABASE_URL` in the examples has no `sslmode`. A hosted database needs `?sslmode=require` at least (`verify-full` where the host's certificate allows). The local PostgreSQL has TLS off.
5. The rate limiter is in-memory and per process (limitations item 38), so several server processes each keep their own count.
6. The Next app sets no `Content-Security-Policy`: its inline scripts need a per-request nonce, which belongs with the deployment.
7. The end-to-end suite, `docs/demo.md` and the thesis figures all use `http://127.0.0.1`.
8. HSTS is `max-age` one year with `includeSubDomains` and no `preload`; preloading is a one-way door and should be a deliberate decision once the domain is settled.
