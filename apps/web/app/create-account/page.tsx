"use client";

/** Create an account: phone number, a 4-digit PIN, and the role it belongs to. */

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { PinField, PhoneField, RoleToggle } from "@/components/AuthFields";
import { ApiErrorMessage, homeFor, useRedirectIfSignedIn, useSession } from "@/components/SessionProvider";
import { ApiError, api } from "@/lib/api";
import type { Role } from "@/lib/types";
import styles from "../auth.module.css";

export default function Page() {
  useRedirectIfSignedIn();
  const router = useRouter();
  const { setSession } = useSession();
  const [role, setRole] = useState<Role>("worker");
  const [phone, setPhone] = useState("");
  const [pin, setPin] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    const found: Record<string, string> = {};
    if (!phone.trim()) found.phone = "Enter your phone number.";
    if (pin.length !== 4) found.pin = "Choose a 4-digit PIN.";
    else if (confirmation !== pin) found.confirmation = "The two PINs are different.";
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

          <PhoneField value={phone} onChange={setPhone} error={errors.phone} disabled={busy} />

          <div className={styles.pins}>
            <PinField label="Create a 4-digit PIN" value={pin} onChange={setPin} error={errors.pin} disabled={busy} />
            <PinField
              label="Confirm PIN"
              value={confirmation}
              onChange={setConfirmation}
              error={errors.confirmation}
              disabled={busy}
            />
          </div>

          <button className={`button ${styles.submit}`} type="submit" disabled={busy}>
            {busy ? "Creating your account…" : "Create account"}
          </button>
        </form>

        <p className={styles.alternative}>
          <Link href="/">Already have an account? Sign in</Link>
        </p>
      </div>
    </main>
  );
}
