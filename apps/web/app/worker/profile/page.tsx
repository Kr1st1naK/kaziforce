"use client";

/**
 * Create your worker profile (FR-01). On submit the matching runs and the
 * worker goes to their matches.
 *
 * No name or contact field: profiles hold no personally identifying
 * information (DR-07).
 */

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { AppShell } from "@/components/AppShell";
import { AmountInput, Select, TextArea } from "@/components/FormFields";
import { ApiErrorMessage, useGuard, useSession } from "@/components/SessionProvider";
import { ApiError, api } from "@/lib/api";
import { SUGGESTED_LOCATIONS } from "@/lib/locations";
import { AVAILABILITY, type Availability } from "@/lib/types";
import styles from "./page.module.css";

export default function Page() {
  const waiting = useGuard("worker");
  const { session, refresh } = useSession();
  const router = useRouter();
  const [skills, setSkills] = useState("");
  const [biography, setBiography] = useState("");
  const [location, setLocation] = useState("");
  const [availability, setAvailability] = useState("");
  const [rate, setRate] = useState("");
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);

  const existing = session?.worker_profile_id ?? null;

  useEffect(() => {
    if (!existing) return;
    let cancelled = false;
    api
      .myProfile()
      .then(({ worker }) => {
        if (cancelled) return;
        setSkills(worker.skills.join(", "));
        setBiography(worker.biography);
        setLocation(worker.location ?? "");
        setAvailability(worker.availability ?? "");
        setRate(worker.rate_expectation === null ? "" : String(worker.rate_expectation));
      })
      .catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, [existing]);

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    const found: Record<string, string> = {};
    if (!skills.trim()) found.skills = "Tell us what work you do.";
    if (!biography.trim()) found.biography = "Add a short description of your work.";
    if (!location) found.location = "Choose where you work.";
    setErrors(found);
    if (Object.keys(found).length > 0) return;

    setBusy(true);
    try {
      await api.createWorker({
        biography: biography.trim(),
        skills: skills
          .split(",")
          .map((entry) => entry.trim())
          .filter(Boolean),
        location,
        availability: (availability as Availability) || null,
        rate_expectation: rate === "" ? null : Number(rate),
      });
      await refresh();
      router.push("/worker/matches");
    } catch (error) {
      setBusy(false);
      setErrors(
        error instanceof ApiError && error.field
          ? { [error.field.replace("worker.", "")]: error.message }
          : { form: ApiErrorMessage(error) },
      );
    }
  };

  if (waiting) return null;

  return (
    <AppShell>
      <h1>Create your worker profile</h1>
      <p className={`subtitle ${styles.subtitle}`}>Tell us about your work. We&apos;ll find jobs that suit you.</p>

      <div className="card">
        {errors.form && (
          <div className={`alert ${styles.alert}`} role="alert">
            {errors.form}
          </div>
        )}

        <form onSubmit={submit} noValidate>
          <TextArea
            label="What work do you do?"
            required
            value={skills}
            onChange={setSkills}
            error={errors.skills}
            rows={3}
            maxLength={2000}
            hint="Use your own words, in English or Kiswahili. For example: fundi wa umeme, wiring, solar installation."
          />

          <TextArea
            label="About you"
            required
            value={biography}
            onChange={setBiography}
            error={errors.biography}
            rows={3}
            maxLength={4000}
            hint="A short description of your work and how long you've been doing it."
          />

          <Select
            label="Where do you work?"
            required
            value={location}
            onChange={setLocation}
            options={SUGGESTED_LOCATIONS}
            placeholder="Select location"
            error={errors.location}
          />

          <Select
            label="When can you work?"
            value={availability}
            onChange={setAvailability}
            options={AVAILABILITY}
            placeholder="Select availability"
            error={errors.availability}
          />

          <AmountInput
            label="Your daily rate"
            value={rate}
            onChange={setRate}
            placeholder="e.g. 2500"
            error={errors.rate_expectation}
            hint="Adding this helps us find better matches."
          />

          <div className={styles.actions}>
            <button type="button" className="link" onClick={() => router.back()} disabled={busy}>
              Cancel
            </button>
            <button className="button" type="submit" disabled={busy}>
              {busy ? "Finding your matches…" : "Create profile"}
            </button>
          </div>
        </form>
      </div>
    </AppShell>
  );
}
