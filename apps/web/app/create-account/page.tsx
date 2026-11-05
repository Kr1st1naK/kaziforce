"use client";

/**
 * Create an account: phone number, a 4-digit PIN, and the role it belongs to.
 *
 * The confirmation PIN is typed, never prefilled from the first one. Prefilling it
 * would remove the only thing it does: a PIN mistyped once would be confirmed
 * against itself and the person would be locked out of their own account. Instead
 * the mismatch is reported as soon as the second PIN is complete, and either field
 * can be revealed to check it.
 */

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";
import { PIN_LENGTH, PinField, PhoneField, RoleToggle } from "@/components/AuthFields";
import { ApiErrorMessage, homeFor, useRedirectIfSignedIn, useSession } from "@/components/SessionProvider";
import { ApiError, api } from "@/lib/api";
import { phoneError } from "@/lib/phone";
import { ROLES, type Role } from "@/lib/types";
import styles from "../auth.module.css";

const MISMATCH = "The two PINs are different.";

/** The landing page links here with ?role=worker or ?role=client; anything else starts as a worker. */
function startingRole(value: string | null): Role {
  return ROLES.find((role) => role === value) ?? "worker";
}

export default function Page() {
  // useSearchParams needs a Suspense boundary above it for the page to be built statically.
  return (
    <Suspense>
      <CreateAccount />
    </Suspense>
  );
}

function CreateAccount() {
  useRedirectIfSignedIn();
  const router = useRouter();
  const { setSession } = useSession();
  const params = useSearchParams();
  const [role, setRole] = useState<Role>(() => startingRole(params.get("role")));
  const [phone, setPhone] = useState("");
  const [pin, setPin] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);

  // Reported as soon as the second PIN is complete, rather than waiting for submit:
  // the digits are hidden, so the sooner it is said the less there is to retype.
  const mismatch = confirmation.length === PIN_LENGTH && confirmation !== pin;

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    const found: Record<string, string> = {};
    const badPhone = phoneError(phone);
    if (badPhone) found.phone = badPhone;
    if (pin.length !== PIN_LENGTH) found.pin = `Choose a ${PIN_LENGTH}-digit PIN.`;
    else if (confirmation !== pin) found.confirmation = MISMATCH;
    setErrors(found);
    if (Object.keys(found).length > 0) return;

    setBusy(true);
    try {
      const session = await api.createAccount({ phone, pin, role });
      // See the note in app/page.tsx: this route stays mounted but hidden, so
      // the PIN is cleared from state before navigating away.
      setPhone("");
      setPin("");
      setConfirmation("");
      setSession(session);
      router.replace(homeFor(session));
    } catch (error) {
      setBusy(false);
      setErrors(
        error instanceof ApiError && error.field
          ? { [error.field]: error.message }
          : { form: ApiErrorMessage(error) },
      );
    }
  };

  return (
    <main className={styles.centre}>
      <div className={`card ${styles.card}`}>
        <h1 className={styles.heading}>Create an account</h1>
        <p className={`subtitle ${styles.subtitle}`}>Job matching for Kenyan trades.</p>

        <form onSubmit={submit} noValidate>
          <RoleToggle role={role} onChange={setRole} disabled={busy} />

          {errors.form && (
            <div className={`alert ${styles.alert}`} role="alert">
              {errors.form}
            </div>
          )}

          <PhoneField
            value={phone}
            onChange={setPhone}
            error={errors.phone}
            hint="Your Kenyan mobile number without the leading 0."
            disabled={busy}
          />

          <PinField
            label={`Create a ${PIN_LENGTH}-digit PIN`}
            value={pin}
            onChange={setPin}
            error={errors.pin}
            disabled={busy}
            showToggle
          />
          <PinField
            label="Confirm PIN"
            value={confirmation}
            onChange={setConfirmation}
            error={errors.confirmation ?? (mismatch ? MISMATCH : undefined)}
            disabled={busy}
            showToggle
          />

          <button className={`button ${styles.submit}`} type="submit" disabled={busy}>
            {busy ? "Creating your account…" : "Create account"}
          </button>
        </form>

        <p className={styles.alternative}>
          <Link href="/sign-in">Already have an account? Sign in</Link>
        </p>
      </div>
    </main>
  );
}
