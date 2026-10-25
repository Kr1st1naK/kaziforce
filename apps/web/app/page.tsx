"use client";

/** Sign in. Everyone lands here; the role toggle decides which account is expected. */

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { PinField, PhoneField, RoleToggle } from "@/components/AuthFields";
import { ApiErrorMessage, homeFor, useRedirectIfSignedIn, useSession } from "@/components/SessionProvider";
import { ApiError, api } from "@/lib/api";
import type { Role } from "@/lib/types";
import styles from "./auth.module.css";

export default function Page() {
  useRedirectIfSignedIn();
  const router = useRouter();
  const { setSession } = useSession();
  const [role, setRole] = useState<Role>("worker");
  const [phone, setPhone] = useState("");
  const [pin, setPin] = useState("");
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    const found: Record<string, string> = {};
    if (!phone.trim()) found.phone = "Enter your phone number.";
    if (pin.length !== 4) found.pin = "Enter your 4-digit PIN.";
    setErrors(found);
    if (Object.keys(found).length > 0) return;

    setBusy(true);
    try {
      const session = await api.signIn({ phone, pin });
      // Cleared before leaving: Next keeps this route mounted in a hidden
      // Activity for back navigation, so anything left in state stays in the
      // DOM for the rest of the session. A PIN must not.
      setPhone("");
      setPin("");
      setSession(session);
      if (session.account.role !== role) {
        setRole(session.account.role);
      }
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
        <form onSubmit={submit} noValidate>
          <RoleToggle role={role} onChange={setRole} bordered={false} disabled={busy} />

          {errors.form && (
            <div className={`alert ${styles.alert}`} role="alert">
              {errors.form}
            </div>
          )}

          <PhoneField value={phone} onChange={setPhone} error={errors.phone} disabled={busy} />
          <PinField label="4-digit PIN" value={pin} onChange={setPin} error={errors.pin} disabled={busy} showToggle />

          <button className={`button ${styles.submit}`} type="submit" disabled={busy}>
            {busy ? "Signing in…" : "Continue"}
          </button>
        </form>

        <p className={styles.alternative}>
          <Link href="/create-account">New here? Create an account</Link>
        </p>
      </div>
    </main>
  );
}
