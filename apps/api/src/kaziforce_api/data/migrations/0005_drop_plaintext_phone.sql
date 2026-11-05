-- 0005: remove the plaintext phone column, once every account has an encrypted one.
--
-- This refuses to run while any account lacks phone_hash or phone_enc, which is the state
-- 0004 leaves existing accounts in. The backfill (python -m kaziforce_api.data.backfill_contact)
-- fills them and checks each by decrypting it and recomputing its hash; run it, then migrate again.
-- On a database with no accounts, which is every fresh build, this runs straight through.
--
-- To undo it: python -m kaziforce_api.data.backfill_contact --restore-plaintext
-- (needs the same keys), or restore the backup taken before 0004. See docs/privacy-and-keys.md.

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM account WHERE phone_hash IS NULL OR phone_enc IS NULL) THEN
        RAISE EXCEPTION 'accounts still lack an encrypted phone: run python -m kaziforce_api.data.backfill_contact, then migrate again';
    END IF;
END $$;

ALTER TABLE account DROP CONSTRAINT account_has_phone;
ALTER TABLE account DROP COLUMN phone;
ALTER TABLE account
    ALTER COLUMN phone_hash SET NOT NULL,
    ALTER COLUMN phone_enc SET NOT NULL;
