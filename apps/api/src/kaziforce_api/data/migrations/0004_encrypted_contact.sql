-- 0004: encrypted contact details, consent, and a public identifier for workers.
--
-- A phone number and a name identify a person, so they are no longer stored in clear:
--   phone_hash       HMAC-SHA256 of the normalised number under a separate key. Unique; the
--                    sign-in lookup key, so a number is found without being stored.
--   phone_enc        the number, AES-256-GCM, for display and the tel: link.
--   first_name_enc,  a worker's name, AES-256-GCM. Names live on the account, not on
--   last_name_enc    worker_profile, so the matching data stays free of personal data (DR-07).
--   contact_consent  the worker's own choice that clients may see their name and number. Off by
--                    default; the CHECK below stops it being on without a name to show.
--
-- The plaintext `phone` column stays until 0005, which refuses to run until every account has
-- been backfilled. Run the backfill between the two:
--     python -m kaziforce_api.data.migrate                 (applies 0004, stops at 0005)
--     python -m kaziforce_api.data.backfill_contact        (encrypts, then verifies by decrypting)
--     python -m kaziforce_api.data.migrate                 (applies 0005)
-- The API must be stopped from the first command to the last: until the backfill has run,
-- existing accounts have no phone_hash and cannot sign in. See docs/privacy-and-keys.md.
--
-- public_id is a random identifier a client can use to open a worker's profile, so the
-- internal worker_id (which /recommend accepts) is never handed out. Every existing profile
-- gets its own value. It is returned only for a worker whose account has consented.

ALTER TABLE account ALTER COLUMN phone DROP NOT NULL;

ALTER TABLE account
    ADD COLUMN phone_hash         CHAR(64),
    ADD COLUMN phone_enc          TEXT,
    ADD COLUMN first_name_enc     TEXT,
    ADD COLUMN last_name_enc      TEXT,
    ADD COLUMN contact_consent    BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN consent_changed_at TIMESTAMPTZ;

CREATE UNIQUE INDEX account_phone_hash_unique ON account (phone_hash) WHERE phone_hash IS NOT NULL;

-- Whatever the code does, an account always has a way to be found and shown.
ALTER TABLE account ADD CONSTRAINT account_has_phone
    CHECK (phone IS NOT NULL OR (phone_hash IS NOT NULL AND phone_enc IS NOT NULL));

ALTER TABLE account ADD CONSTRAINT account_consent_needs_names
    CHECK (NOT contact_consent OR (first_name_enc IS NOT NULL AND last_name_enc IS NOT NULL));

ALTER TABLE worker_profile ADD COLUMN public_id UUID NOT NULL DEFAULT gen_random_uuid();

CREATE UNIQUE INDEX worker_profile_public_id_unique ON worker_profile (public_id);
